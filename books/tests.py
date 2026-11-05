from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse, reverse_lazy

from .forms import BookForm, ThreadForm
from .models import Book, Thread

User = get_user_model()


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
