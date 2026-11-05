from datetime import date
from unittest import addModuleCleanup
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse, reverse_lazy

from .forms import BookForm, ThreadForm
from .models import Book, Comment, Thread

User = get_user_model()


def setUpModule():
    # 뷰 테스트가 실제 외부 API를 호출하지 않도록 서비스 함수를 대체한다.
    for name in ('update_author_info', 'generate_thread_cover'):
        patcher = patch(f'books.services.{name}', return_value=True)
        patcher.start()
        addModuleCleanup(patcher.stop)


def make_user(username='reader'):
    return User.objects.create_user(username, password='pw-for-tests-1')


def make_book(user, **fields):
    defaults = {'title': '데미안', 'description': '성장 소설', 'rating': 9, 'author': '헤르만 헤세'}
    return Book.objects.create(user=user, **{**defaults, **fields})


def make_thread(user, book, **fields):
    defaults = {'title': '내면의 거울', 'content': '깊은 감상', 'reading_date': date(2026, 10, 8)}
    return Thread.objects.create(user=user, book=book, **{**defaults, **fields})


class BookModelTests(TestCase):
    """F604 books Model Class (Book)"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def test_book_stores_required_fields_and_author_relation(self):
        book = make_book(self.user)
        book.refresh_from_db()
        self.assertEqual(
            (book.title, book.description, book.rating, book.author),
            ('데미안', '성장 소설', 9, '헤르만 헤세'),
        )
        self.assertIn(book, self.user.book_set.all())

    def test_rating_must_be_between_0_and_10(self):
        for rating in (-0.5, 10.5):
            with self.assertRaises(ValidationError):
                Book(user=self.user, title='t', description='d', author='a', rating=rating).full_clean()
        for rating in (0, 10):
            Book(user=self.user, title='t', description='d', author='a', rating=rating).full_clean()

    def test_newest_book_comes_first(self):
        first, second = make_book(self.user), make_book(self.user)
        self.assertEqual(list(Book.objects.all()), [second, first])


class ThreadModelTests(TestCase):
    """F605 books Model Class (Thread)"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.book = make_book(cls.user)

    def test_thread_stores_required_fields(self):
        thread = make_thread(self.user, self.book)
        thread.refresh_from_db()
        self.assertEqual(thread.title, '내면의 거울')
        self.assertEqual(thread.content, '깊은 감상')
        self.assertEqual(thread.reading_date, date(2026, 10, 8))
        self.assertIsNotNone(thread.created_at)
        self.assertIsNotNone(thread.updated_at)

    def test_thread_relations(self):
        thread = make_thread(self.user, self.book)
        fan = make_user('fan')
        thread.like_users.add(fan)
        self.assertIn(thread, self.book.thread_set.all())
        self.assertIn(thread, self.user.thread_set.all())
        self.assertIn(thread, fan.like_threads.all())
        self.assertIn(fan, thread.like_users.all())

    def test_deleting_book_deletes_its_threads(self):
        make_thread(self.user, self.book)
        Book.objects.filter(pk=self.book.pk).delete()
        self.assertFalse(Thread.objects.exists())


class BookThreadFormTests(TestCase):
    """F606 books Form Class"""

    def test_book_form_accepts_valid_data(self):
        form = BookForm({'title': '데미안', 'description': '설명', 'rating': 9.5, 'author': '헤르만 헤세'})
        self.assertTrue(form.is_valid())

    def test_book_form_rejects_invalid_data(self):
        form = BookForm({'title': '', 'description': '설명', 'rating': 11, 'author': '헤르만 헤세'})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('rating', form.errors)

    def test_book_form_does_not_expose_owner(self):
        self.assertNotIn('user', BookForm().fields)

    def test_thread_form_rejects_invalid_date(self):
        form = ThreadForm({'title': '제목', 'content': '내용', 'reading_date': 'not-a-date'})
        self.assertFalse(form.is_valid())
        self.assertIn('reading_date', form.errors)

    def test_thread_form_prefills_date_in_iso_format(self):
        user = make_user()
        thread = make_thread(user, make_book(user))
        self.assertIn('value="2026-10-08"', ThreadForm(instance=thread)['reading_date'].as_widget())

    def test_thread_form_does_not_expose_relations(self):
        fields = ThreadForm().fields
        for name in ('user', 'book', 'like_users'):
            self.assertNotIn(name, fields)


class IndexViewTests(TestCase):
    """F615 index"""

    url = reverse_lazy('books:index')

    def test_shows_every_book_with_detail_link_without_login(self):
        user = make_user()
        books = [make_book(user, title='데미안'), make_book(user, title='노인과 바다')]
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for book in books:
            self.assertContains(response, book.title)
            self.assertContains(response, reverse('books:detail', args=[book.pk]))

    def test_empty_state_message(self):
        self.assertContains(self.client.get(self.url), '등록된 도서가 없습니다.')


class CreateViewTests(TestCase):
    """F616 create"""

    url = reverse_lazy('books:create')

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def data(self, **overrides):
        return {'title': '데미안', 'description': '설명', 'rating': 9, 'author': '헤르만 헤세', **overrides}

    def test_get_renders_form_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="title"')

    def test_valid_post_saves_with_current_user_and_redirects_to_detail(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data())
        book = Book.objects.get()
        self.assertEqual(book.user, self.user)
        self.assertRedirects(response, reverse('books:detail', args=[book.pk]))

    def test_invalid_post_shows_error_and_saves_nothing(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data(rating=11))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'text-danger')
        self.assertFalse(Book.objects.exists())

    def test_anonymous_user_cannot_create(self):
        for response in (self.client.get(self.url), self.client.post(self.url, self.data())):
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
        self.assertFalse(Book.objects.exists())


class DetailViewTests(TestCase):
    """F617 detail"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user('owner')
        cls.other = make_user('other')
        cls.book = make_book(cls.owner, rating=8.5)
        cls.url = reverse('books:detail', args=[cls.book.pk])

    def test_shows_book_fields_and_back_link(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in ('데미안', '성장 소설', '8.5 / 10', '헤르만 헤세', reverse('books:index')):
            self.assertContains(response, text)

    def test_lists_only_threads_of_this_book(self):
        thread = make_thread(self.owner, self.book, title='이 책의 쓰레드')
        make_thread(self.owner, make_book(self.owner, title='다른 책'), title='다른 책의 쓰레드')
        response = self.client.get(self.url)
        self.assertContains(response, '이 책의 쓰레드')
        self.assertContains(response, reverse('books:thread_detail', args=[thread.pk]))
        self.assertNotContains(response, '다른 책의 쓰레드')

    def test_owner_sees_update_and_delete(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, reverse('books:update', args=[self.book.pk]))
        self.assertContains(response, reverse('books:delete', args=[self.book.pk]))

    def test_others_do_not_see_update_and_delete(self):
        for login in (False, True):
            if login:
                self.client.force_login(self.other)
            response = self.client.get(self.url)
            self.assertNotContains(response, reverse('books:update', args=[self.book.pk]))
            self.assertNotContains(response, reverse('books:delete', args=[self.book.pk]))

    def test_thread_create_link_is_shown_only_when_logged_in(self):
        link = reverse('books:thread_create', args=[self.book.pk])
        self.assertNotContains(self.client.get(self.url), link)
        self.client.force_login(self.other)
        self.assertContains(self.client.get(self.url), link)

    def test_unknown_book_returns_404(self):
        self.assertEqual(self.client.get(reverse('books:detail', args=[99999])).status_code, 404)


class UpdateViewTests(TestCase):
    """F618 update"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user('owner')
        cls.other = make_user('other')
        cls.book = make_book(cls.owner)
        cls.url = reverse('books:update', args=[cls.book.pk])

    def data(self, **overrides):
        return {'title': '수정된 제목', 'description': '수정된 설명', 'rating': 7, 'author': '헤르만 헤세', **overrides}

    def test_get_prefills_previous_data(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, 'value="데미안"')
        self.assertContains(response, '성장 소설')

    def test_valid_post_saves_and_redirects_to_detail(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.data())
        self.assertRedirects(response, reverse('books:detail', args=[self.book.pk]))
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, '수정된 제목')

    def test_invalid_post_shows_error_and_keeps_data(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.data(rating=-1))
        self.assertContains(response, 'text-danger')
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, '데미안')

    def test_only_owner_can_update(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, '데미안')

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.post(self.url, self.data())
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")


class DeleteViewTests(TestCase):
    """F619 delete"""

    def setUp(self):
        self.owner = make_user('owner')
        self.other = make_user('other')
        self.book = make_book(self.owner)
        self.url = reverse('books:delete', args=[self.book.pk])

    def test_owner_post_deletes_and_redirects_to_main(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('books:index'))
        self.assertFalse(Book.objects.exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(Book.objects.exists())

    def test_get_is_not_allowed_even_for_anonymous_user(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(Book.objects.exists())


class ThreadCreateViewTests(TestCase):
    """F620 thread_create"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.book = make_book(cls.user)
        cls.url = reverse('books:thread_create', args=[cls.book.pk])

    def data(self, **overrides):
        return {'title': '감상', 'content': '내용', 'reading_date': '2026-10-08', **overrides}

    def test_get_renders_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="date"')

    def test_valid_post_saves_relations_and_redirects_to_thread_detail(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data())
        thread = Thread.objects.get()
        self.assertEqual((thread.user, thread.book), (self.user, self.book))
        self.assertRedirects(response, reverse('books:thread_detail', args=[thread.pk]))

    def test_invalid_post_shows_error_and_saves_nothing(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.data(reading_date=''))
        self.assertContains(response, 'text-danger')
        self.assertFalse(Thread.objects.exists())

    def test_anonymous_user_cannot_create(self):
        response = self.client.post(self.url, self.data())
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
        self.assertFalse(Thread.objects.exists())


class ThreadDetailViewTests(TestCase):
    """F621 thread_detail"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user('owner')
        cls.other = make_user('other')
        cls.book = make_book(cls.owner)
        cls.thread = make_thread(cls.owner, cls.book)
        cls.url = reverse('books:thread_detail', args=[cls.thread.pk])

    def test_shows_thread_fields_and_back_link(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in ('내면의 거울', '깊은 감상', '2026년 10월 8일', reverse('books:detail', args=[self.book.pk])):
            self.assertContains(response, text)

    def test_content_is_escaped(self):
        thread = make_thread(self.owner, self.book, content='<script>alert(1)</script>')
        response = self.client.get(reverse('books:thread_detail', args=[thread.pk]))
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_owner_sees_update_and_delete(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, reverse('books:thread_update', args=[self.thread.pk]))
        self.assertContains(response, reverse('books:thread_delete', args=[self.thread.pk]))

    def test_others_do_not_see_update_and_delete(self):
        for login in (False, True):
            if login:
                self.client.force_login(self.other)
            response = self.client.get(self.url)
            self.assertNotContains(response, reverse('books:thread_update', args=[self.thread.pk]))
            self.assertNotContains(response, reverse('books:thread_delete', args=[self.thread.pk]))


class ThreadUpdateViewTests(TestCase):
    """F622 thread_update"""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user('owner')
        cls.other = make_user('other')
        cls.thread = make_thread(cls.owner, make_book(cls.owner))
        cls.url = reverse('books:thread_update', args=[cls.thread.pk])

    def data(self, **overrides):
        return {'title': '수정된 감상', 'content': '수정된 내용', 'reading_date': '2026-11-01', **overrides}

    def test_get_prefills_previous_data_including_date(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertContains(response, 'value="내면의 거울"')
        self.assertContains(response, '깊은 감상')
        self.assertContains(response, 'value="2026-10-08"')

    def test_valid_post_saves_and_redirects_to_thread_detail(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.data())
        self.assertRedirects(response, reverse('books:thread_detail', args=[self.thread.pk]))
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.title, '수정된 감상')

    def test_invalid_post_shows_error_and_keeps_data(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, self.data(title=''))
        self.assertContains(response, 'text-danger')
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.title, '내면의 거울')

    def test_only_owner_can_update(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.title, '내면의 거울')


class ThreadDeleteViewTests(TestCase):
    """F623 thread_delete"""

    def setUp(self):
        self.owner = make_user('owner')
        self.other = make_user('other')
        self.book = make_book(self.owner)
        self.thread = make_thread(self.owner, self.book)
        self.url = reverse('books:thread_delete', args=[self.thread.pk])

    def test_owner_post_deletes_and_redirects_to_book_detail(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('books:detail', args=[self.book.pk]))
        self.assertFalse(Thread.objects.exists())

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(Thread.objects.exists())

    def test_get_is_not_allowed_even_for_anonymous_user(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(Thread.objects.exists())


class LikeViewTests(TestCase):
    """F624 like"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.thread = make_thread(cls.user, make_book(cls.user))
        cls.url = reverse('books:like', args=[cls.thread.pk])
        cls.detail_url = reverse('books:thread_detail', args=[cls.thread.pk])

    def test_post_toggles_like_and_returns_to_thread_detail(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post(self.url), self.detail_url)
        self.assertIn(self.user, self.thread.like_users.all())
        self.assertRedirects(self.client.post(self.url), self.detail_url)
        self.assertNotIn(self.user, self.thread.like_users.all())

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_anonymous_post_is_sent_to_login(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")
        self.assertFalse(self.thread.like_users.exists())

    def test_button_label_and_count_follow_like_state(self):
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url)
        self.assertContains(response, '>좋아요<')
        self.assertContains(response, '0 좋아요')

        self.thread.like_users.add(self.user)
        response = self.client.get(self.detail_url)
        self.assertContains(response, '좋아요 취소')
        self.assertContains(response, '1 좋아요')

    def test_button_is_hidden_from_anonymous_user(self):
        self.assertNotContains(self.client.get(self.detail_url), self.url)


class AuthorInfoViewTests(TestCase):
    """F625 정보 생성 및 저장"""

    NOTICE = '작가 대표작과 작가 정보는 AI가 생성한 정보로, 정확하지 않을 수 있습니다.'

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        self.client.force_login(self.user)

    def book_data(self, **overrides):
        return {'title': '데미안', 'description': '설명', 'rating': 9, 'author': '헤르만 헤세', **overrides}

    def test_create_requests_author_info(self):
        with patch('books.services.update_author_info', return_value=True) as mock_update:
            self.client.post(reverse('books:create'), self.book_data())
        mock_update.assert_called_once_with(Book.objects.get())

    def test_create_keeps_book_and_warns_when_ai_fails(self):
        with patch('books.services.update_author_info', return_value=False):
            response = self.client.post(reverse('books:create'), self.book_data(), follow=True)
        self.assertEqual(Book.objects.count(), 1)
        self.assertContains(response, '작가 정보를 불러오지 못했습니다.')

    def test_update_regenerates_only_when_author_changes(self):
        book = make_book(self.user)
        url = reverse('books:update', args=[book.pk])
        with patch('books.services.update_author_info', return_value=True) as mock_update:
            self.client.post(url, self.book_data(description='설명만 변경'))
            mock_update.assert_not_called()
            self.client.post(url, self.book_data(author='어니스트 헤밍웨이'))
            mock_update.assert_called_once()

    def test_detail_shows_author_info_with_notice(self):
        book = make_book(
            self.user, author_info='독일계 스위스 작가', author_works='데미안, 싯다르타',
            author_image_url='https://img.example/hesse.jpg',
        )
        response = self.client.get(reverse('books:detail', args=[book.pk]))
        for text in ('독일계 스위스 작가', '데미안, 싯다르타', 'https://img.example/hesse.jpg', self.NOTICE):
            self.assertContains(response, text)

    def test_detail_hides_section_without_author_info(self):
        response = self.client.get(reverse('books:detail', args=[make_book(self.user).pk]))
        self.assertNotContains(response, self.NOTICE)

    def test_form_does_not_expose_generated_fields(self):
        for name in ('author_info', 'author_works', 'author_image_url'):
            self.assertNotIn(name, BookForm().fields)


class ThreadCoverViewTests(TestCase):
    """F626 커버 이미지"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.book = make_book(cls.user)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('books:thread_create', args=[self.book.pk])
        self.data = {'title': '감상', 'content': '내용', 'reading_date': '2026-10-08'}

    def test_thread_create_requests_cover(self):
        with patch('books.services.generate_thread_cover', return_value=True) as mock_cover:
            self.client.post(self.url, self.data)
        mock_cover.assert_called_once_with(Thread.objects.get())

    def test_invalid_thread_does_not_request_cover(self):
        with patch('books.services.generate_thread_cover', return_value=True) as mock_cover:
            self.client.post(self.url, {**self.data, 'title': ''})
        mock_cover.assert_not_called()

    def test_thread_is_kept_with_warning_when_cover_fails(self):
        with patch('books.services.generate_thread_cover', return_value=False):
            response = self.client.post(self.url, self.data, follow=True)
        self.assertEqual(Thread.objects.count(), 1)
        self.assertContains(response, '커버 이미지를 생성하지 못했습니다.')

    def test_thread_update_does_not_regenerate_cover(self):
        thread = make_thread(self.user, self.book)
        with patch('books.services.generate_thread_cover', return_value=True) as mock_cover:
            self.client.post(reverse('books:thread_update', args=[thread.pk]), self.data)
        mock_cover.assert_not_called()

    def test_detail_shows_cover_only_when_present(self):
        thread = make_thread(self.user, self.book)
        url = reverse('books:thread_detail', args=[thread.pk])
        self.assertNotContains(self.client.get(url), '커버 이미지"')

        Thread.objects.filter(pk=thread.pk).update(cover_image='thread_covers/thread_1.png')
        self.assertContains(self.client.get(url), 'thread_covers/thread_1.png')

    def test_form_does_not_expose_cover_field(self):
        self.assertNotIn('cover_image', ThreadForm().fields)


class CommentViewTests(TestCase):
    """F627 쓰레드 댓글"""

    @classmethod
    def setUpTestData(cls):
        cls.writer = make_user('writer')
        cls.other = make_user('other')
        cls.thread = make_thread(cls.writer, make_book(cls.writer))
        cls.detail_url = reverse('books:thread_detail', args=[cls.thread.pk])
        cls.create_url = reverse('books:comment_create', args=[cls.thread.pk])

    def delete_url(self, comment):
        return reverse('books:comment_delete', args=[self.thread.pk, comment.pk])

    def make_comment(self, user=None, content='공감합니다'):
        return Comment.objects.create(thread=self.thread, user=user or self.writer, content=content)

    def test_valid_post_saves_with_current_user_and_returns_to_thread(self):
        self.client.force_login(self.other)
        response = self.client.post(self.create_url, {'content': '공감합니다'})
        self.assertRedirects(response, self.detail_url)
        comment = Comment.objects.get()
        self.assertEqual((comment.user, comment.thread, comment.content), (self.other, self.thread, '공감합니다'))

    def test_blank_comment_shows_error_and_saves_nothing(self):
        self.client.force_login(self.other)
        for content in ('', '   '):
            response = self.client.post(self.create_url, {'content': content})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'text-danger')
        self.assertFalse(Comment.objects.exists())

    def test_too_long_comment_is_rejected(self):
        self.client.force_login(self.other)
        self.client.post(self.create_url, {'content': 'x' * 201})
        self.assertFalse(Comment.objects.exists())

    def test_anonymous_user_cannot_comment_and_sees_no_form(self):
        response = self.client.post(self.create_url, {'content': '공감합니다'})
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.create_url}")
        self.assertFalse(Comment.objects.exists())
        self.assertNotContains(self.client.get(self.detail_url), self.create_url)

    def test_list_links_to_author_profile(self):
        self.make_comment(self.other)
        response = self.client.get(self.detail_url)
        self.assertContains(response, '공감합니다')
        self.assertContains(response, reverse('accounts:profile', args=['other']))

    def test_delete_button_is_shown_only_to_comment_author(self):
        comment = self.make_comment(self.other)
        self.assertNotContains(self.client.get(self.detail_url), self.delete_url(comment))
        self.client.force_login(self.writer)
        self.assertNotContains(self.client.get(self.detail_url), self.delete_url(comment))
        self.client.force_login(self.other)
        self.assertContains(self.client.get(self.detail_url), self.delete_url(comment))

    def test_author_can_delete_but_others_cannot(self):
        comment = self.make_comment(self.other)
        self.client.force_login(self.writer)
        self.assertEqual(self.client.post(self.delete_url(comment)).status_code, 403)
        self.assertTrue(Comment.objects.exists())

        self.client.force_login(self.other)
        self.assertRedirects(self.client.post(self.delete_url(comment)), self.detail_url)
        self.assertFalse(Comment.objects.exists())

    def test_comment_cannot_be_deleted_through_another_thread(self):
        comment = self.make_comment(self.other)
        another = make_thread(self.writer, self.thread.book)
        self.client.force_login(self.other)
        response = self.client.post(reverse('books:comment_delete', args=[another.pk, comment.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Comment.objects.exists())

    def test_delete_does_not_allow_get(self):
        comment = self.make_comment(self.other)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.delete_url(comment)).status_code, 405)
