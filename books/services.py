"""외부 서비스 연동: 위키피디아 검색과 생성형 AI 호출 (F625).

외부 서비스가 실패해도 도서 저장은 유지되어야 하므로, 뷰에서 호출하는 함수는
예외를 전파하지 않고 성공 여부를 bool로 반환한다.
"""
import json
import logging

import requests
from django.conf import settings
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)

WIKI_LANGUAGES = ('ko', 'en')
WIKI_TIMEOUT_SECONDS = 5
WIKI_EXTRACT_LIMIT = 2000
WIKI_HEADERS = {'User-Agent': 'ThRead-book-community/1.0 (educational project)'}

AI_TIMEOUT_SECONDS = 60

AUTHOR_SYSTEM_PROMPT = """당신은 도서 커뮤니티의 작가 소개 편집자입니다.
사용자가 제공한 도서 정보와 위키피디아 발췌를 바탕으로 작가 정보를 작성합니다.
- 위키피디아 발췌가 이 도서의 작가와 같은 인물인지 먼저 판단합니다. 다른 인물이면 발췌 내용을 사용하지 않습니다.
- 확실하지 않은 사실과 작품명은 지어내지 말고 생략합니다.
- 반드시 다음 세 개의 키를 가진 JSON 객체로만 응답합니다.
  - author_info (문자열): 이 작가를 소개하는 한국어 문장 2~3개. 작가를 식별할 수 없으면 빈 문자열.
  - author_works (문자열 배열): 실제로 존재한다고 확신하는 대표작 제목. 최대 5개.
  - wiki_matches (불리언): 위키피디아 발췌가 이 작가에 대한 내용이면 true, 아니면 false."""


class AIServiceError(Exception):
    """AI 호출 결과를 사용할 수 없을 때 발생한다."""


def _openai_client():
    if not settings.GMS_KEY:
        raise AIServiceError('GMS_KEY가 설정되지 않았습니다.')
    return OpenAI(
        api_key=settings.GMS_KEY,
        base_url=settings.GMS_BASE_URL,
        timeout=AI_TIMEOUT_SECONDS,
        max_retries=1,
    )


def _ask_gpt_json(system_prompt, user_prompt):
    response = _openai_client().chat.completions.create(
        model=settings.GPT_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        response_format={'type': 'json_object'},
        # minimal에서는 존재하지 않는 작품명을 지어내는 경우가 있어 low를 사용한다.
        reasoning_effort='low',
    )
    try:
        data = json.loads(response.choices[0].message.content)
    except (IndexError, TypeError, ValueError) as error:
        raise AIServiceError('GPT 응답을 JSON으로 해석할 수 없습니다.') from error
    if not isinstance(data, dict):
        raise AIServiceError('GPT 응답이 JSON 객체가 아닙니다.')
    return data


def search_author_on_wikipedia(author):
    """작가 이름으로 위키피디아를 검색해 문서 제목, 발췌, 사진 URL을 반환한다. 없으면 None."""
    params = {
        'action': 'query',
        'format': 'json',
        'redirects': 1,
        'generator': 'search',
        'gsrsearch': author,
        'gsrlimit': 1,
        'prop': 'extracts|pageimages|pageprops',
        'exintro': 1,
        'explaintext': 1,
        'piprop': 'thumbnail',
        'pithumbsize': 500,
        'ppprop': 'disambiguation',
    }
    for language in WIKI_LANGUAGES:
        try:
            response = requests.get(
                f'https://{language}.wikipedia.org/w/api.php',
                params=params,
                headers=WIKI_HEADERS,
                timeout=WIKI_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            pages = response.json().get('query', {}).get('pages', {})
        except (requests.RequestException, ValueError) as error:
            logger.warning('위키피디아(%s) 검색 실패: %s', language, error)
            continue

        for page in pages.values():
            if 'disambiguation' in page.get('pageprops', {}) or not page.get('extract'):
                continue
            return {
                'title': page.get('title', ''),
                'extract': page['extract'][:WIKI_EXTRACT_LIMIT],
                'image_url': page.get('thumbnail', {}).get('source', ''),
            }
    return None


def update_author_info(book):
    """book의 작가 정보를 새로 생성해 저장한다.

    실패하면 이전 작가의 정보가 남지 않도록 비워서 저장하고 False를 반환한다.
    """
    book.author_info = book.author_works = book.author_image_url = ''

    wiki = search_author_on_wikipedia(book.author)
    user_prompt = (
        f'도서 제목: {book.title}\n'
        f'작가 이름: {book.author}\n'
        f"위키피디아 문서 제목: {wiki['title'] if wiki else '검색 결과 없음'}\n"
        f"위키피디아 발췌: {wiki['extract'] if wiki else '없음'}"
    )

    success = False
    try:
        profile = _ask_gpt_json(AUTHOR_SYSTEM_PROMPT, user_prompt)
        author_info = str(profile.get('author_info') or '').strip()
        if not author_info:
            raise AIServiceError('작가를 식별하지 못했습니다.')
    except (AIServiceError, OpenAIError) as error:
        logger.warning('작가 정보 생성 실패(book=%s): %s', book.pk, error)
    else:
        works = profile.get('author_works')
        if isinstance(works, list):
            works = ', '.join(str(work).strip() for work in works if str(work).strip())
        book.author_info = author_info
        book.author_works = works.strip() if isinstance(works, str) else ''
        if wiki and profile.get('wiki_matches') is True:
            book.author_image_url = wiki['image_url']
        success = True

    book.save(update_fields=['author_info', 'author_works', 'author_image_url'])
    return success
