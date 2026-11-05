import json
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from openai import OpenAIError

from . import services
from .models import Book

User = get_user_model()


def wiki_page(title='헤르만 헤세', extract='독일계 스위스 작가', image='https://img.example/hesse.jpg', props=None):
    page = {'title': title, 'extract': extract, 'thumbnail': {'source': image}}
    if props:
        page['pageprops'] = props
    return page


def wiki_response(*pages):
    response = MagicMock()
    response.json.return_value = {'query': {'pages': {str(i): page for i, page in enumerate(pages)}}} if pages else {}
    return response


def gpt_client(content):
    client = MagicMock()
    client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content=content))]
    return client


class WikipediaSearchTests(TestCase):
    """F625 위키피디아 검색"""

    @patch('books.services.requests.get')
    def test_returns_first_korean_result(self, mock_get):
        mock_get.return_value = wiki_response(wiki_page())
        result = services.search_author_on_wikipedia('헤르만 헤세')
        self.assertEqual(result['title'], '헤르만 헤세')
        self.assertEqual(result['image_url'], 'https://img.example/hesse.jpg')
        self.assertEqual(mock_get.call_count, 1)
        self.assertIn('ko.wikipedia.org', mock_get.call_args.args[0])
        self.assertEqual(mock_get.call_args.kwargs['params']['gsrsearch'], '헤르만 헤세')

    @patch('books.services.requests.get')
    def test_falls_back_to_english_when_korean_has_no_result(self, mock_get):
        mock_get.side_effect = [wiki_response(), wiki_response(wiki_page(title='Hermann Hesse'))]
        self.assertEqual(services.search_author_on_wikipedia('Hesse')['title'], 'Hermann Hesse')
        self.assertIn('en.wikipedia.org', mock_get.call_args.args[0])

    @patch('books.services.requests.get')
    def test_skips_disambiguation_page(self, mock_get):
        mock_get.return_value = wiki_response(wiki_page(props={'disambiguation': ''}))
        self.assertIsNone(services.search_author_on_wikipedia('김철수'))

    @patch('books.services.requests.get', side_effect=requests.ConnectionError('down'))
    def test_network_failure_returns_none(self, mock_get):
        self.assertIsNone(services.search_author_on_wikipedia('헤르만 헤세'))


@override_settings(GMS_KEY='test-key')
class UpdateAuthorInfoTests(TestCase):
    """F625 정보 생성 및 저장"""

    def setUp(self):
        user = User.objects.create_user('reader', password='pw-for-tests-1')
        self.book = Book.objects.create(user=user, title='데미안', description='d', rating=9, author='헤르만 헤세')
        wiki_patcher = patch('books.services.requests.get', return_value=wiki_response(wiki_page()))
        self.mock_wiki = wiki_patcher.start()
        self.addCleanup(wiki_patcher.stop)

    def run_with_gpt(self, content):
        with patch('books.services._openai_client', return_value=gpt_client(content)) as mock_client:
            result = services.update_author_info(self.book)
        self.book.refresh_from_db()
        return result, mock_client

    def test_saves_generated_info_and_wikipedia_image(self):
        result, mock_client = self.run_with_gpt(json.dumps({
            'author_info': '독일계 스위스 작가입니다.',
            'author_works': ['데미안', '싯다르타'],
            'wiki_matches': True,
        }))
        self.assertTrue(result)
        self.assertEqual(self.book.author_info, '독일계 스위스 작가입니다.')
        self.assertEqual(self.book.author_works, '데미안, 싯다르타')
        self.assertEqual(self.book.author_image_url, 'https://img.example/hesse.jpg')

        request = mock_client.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(request['model'], 'gpt-5-nano')
        self.assertEqual(request['response_format'], {'type': 'json_object'})
        prompt = request['messages'][1]['content']
        self.assertIn('헤르만 헤세', prompt)
        self.assertIn('독일계 스위스 작가', prompt)

    def test_mismatched_wikipedia_person_drops_image(self):
        result, _ = self.run_with_gpt(json.dumps({
            'author_info': '소개', 'author_works': [], 'wiki_matches': False,
        }))
        self.assertTrue(result)
        self.assertEqual(self.book.author_image_url, '')

    def test_works_as_string_is_accepted(self):
        _, _ = self.run_with_gpt(json.dumps({'author_info': '소개', 'author_works': '데미안, 싯다르타'}))
        self.assertEqual(self.book.author_works, '데미안, 싯다르타')

    def test_unknown_author_clears_previous_info(self):
        Book.objects.filter(pk=self.book.pk).update(author_info='이전 작가', author_image_url='https://old/x.jpg')
        self.book.refresh_from_db()
        result, _ = self.run_with_gpt(json.dumps({'author_info': '', 'author_works': []}))
        self.assertFalse(result)
        self.assertEqual((self.book.author_info, self.book.author_image_url), ('', ''))

    def test_invalid_json_returns_false(self):
        for content in ('not json', None, '[1, 2]'):
            result, _ = self.run_with_gpt(content)
            self.assertFalse(result)
            self.assertEqual(self.book.author_info, '')

    def test_api_error_returns_false(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = OpenAIError('boom')
        with patch('books.services._openai_client', return_value=client):
            self.assertFalse(services.update_author_info(self.book))

    @override_settings(GMS_KEY='')
    def test_missing_key_returns_false(self):
        self.assertFalse(services.update_author_info(self.book))
