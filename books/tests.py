from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

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
