import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import include, path, reverse

from books.models import Book, Comment, Thread

User = get_user_model()


class ProjectSetupTests(TestCase):
    """F601 프로젝트 구성"""

    def test_root_redirects_to_main_page(self):
        response = self.client.get('/')
        self.assertRedirects(response, reverse('books:index'))

    def test_every_page_uses_bootstrap_layout(self):
        response = self.client.get(reverse('books:index'))
        self.assertContains(response, 'bootstrap@5.3')
        self.assertContains(response, 'navbar')

    def test_navbar_for_anonymous_user(self):
        response = self.client.get(reverse('books:index'))
        self.assertContains(response, reverse('accounts:login'))
        self.assertContains(response, reverse('accounts:signup'))
        self.assertNotContains(response, reverse('books:create'))
        self.assertNotContains(response, reverse('accounts:logout'))

    def test_navbar_for_authenticated_user(self):
        user = User.objects.create_user('reader', password='pw-for-tests-1')
        self.client.force_login(user)
        response = self.client.get(reverse('books:index'))
        self.assertContains(response, reverse('books:create'))
        self.assertContains(response, reverse('accounts:profile', args=[user.username]))
        self.assertContains(response, reverse('accounts:logout'))
        self.assertNotContains(response, reverse('accounts:login'))
        self.assertNotContains(response, reverse('accounts:signup'))


urlpatterns = [
    path('library/', include('books.urls')),
    path('members/', include('accounts.urls')),
]


class UrlMaintainabilityTests(TestCase):
    """NF602 URL 구성"""

    def test_templates_do_not_hardcode_internal_urls(self):
        pattern = re.compile(r'(?:href|action)="/')
        templates = [
            path_ for root in (settings.BASE_DIR / 'templates', settings.BASE_DIR / 'accounts', settings.BASE_DIR / 'books')
            for path_ in root.rglob('*.html')
        ]
        self.assertTrue(templates)
        for template in templates:
            self.assertIsNone(pattern.search(template.read_text(encoding='utf-8')), template)

    def test_views_do_not_redirect_to_hardcoded_paths(self):
        for view in (settings.BASE_DIR / 'accounts' / 'views.py', settings.BASE_DIR / 'books' / 'views.py'):
            self.assertNotRegex(view.read_text(encoding='utf-8'), r"redirect\(\s*['\"]/")

    @override_settings(ROOT_URLCONF=__name__)
    def test_pages_follow_changed_url_prefixes(self):
        user = User.objects.create_user('reader', password='pw-for-tests-1')
        book = Book.objects.create(user=user, title='데미안', description='d', rating=9, author='a')
        self.client.force_login(user)

        response = self.client.get('/library/')
        self.assertContains(response, f'href="/library/{book.pk}/"')
        self.assertContains(response, 'href="/members/profile/reader/"')
        self.assertContains(response, 'action="/members/logout/"')
        self.assertRedirects(
            self.client.post(f'/library/{book.pk}/delete/'), '/library/', fetch_redirect_response=False,
        )


class HttpMethodTests(TestCase):
    """NF603 HTTP Method 허용"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('reader', password='pw-for-tests-1')
        cls.book = Book.objects.create(user=cls.user, title='데미안', description='d', rating=9, author='a')
        cls.thread = Thread.objects.create(user=cls.user, book=cls.book, title='t', content='c', reading_date='2026-01-01')
        cls.comment = Comment.objects.create(thread=cls.thread, user=cls.user, content='c')

    def routes(self):
        safe, form, post = {'get', 'head'}, {'get', 'head', 'post'}, {'post'}
        return [
            (reverse('accounts:login'), form),
            (reverse('accounts:logout'), post),
            (reverse('accounts:signup'), form),
            (reverse('accounts:profile', args=['reader']), safe),
            (reverse('accounts:follow', args=['reader']), post),
            (reverse('accounts:update'), form),
            (reverse('accounts:delete'), post),
            (reverse('accounts:change_password'), form),
            (reverse('books:index'), safe),
            (reverse('books:create'), form),
            (reverse('books:detail', args=[self.book.pk]), safe),
            (reverse('books:update', args=[self.book.pk]), form),
            (reverse('books:delete', args=[self.book.pk]), post),
            (reverse('books:thread_create', args=[self.book.pk]), form),
            (reverse('books:thread_detail', args=[self.thread.pk]), safe),
            (reverse('books:thread_update', args=[self.thread.pk]), form),
            (reverse('books:thread_delete', args=[self.thread.pk]), post),
            (reverse('books:like', args=[self.thread.pk]), post),
            (reverse('books:comment_create', args=[self.thread.pk]), post),
            (reverse('books:comment_delete', args=[self.thread.pk, self.comment.pk]), post),
        ]

    def assert_disallowed_methods_return_405(self):
        for url, allowed in self.routes():
            for method in {'get', 'head', 'post', 'put', 'patch', 'delete'} - allowed:
                with self.subTest(url=url, method=method):
                    self.assertEqual(getattr(self.client, method)(url).status_code, 405)

    def test_disallowed_methods_return_405_for_anonymous_user(self):
        self.assert_disallowed_methods_return_405()

    def test_disallowed_methods_return_405_for_authenticated_user(self):
        self.client.force_login(self.user)
        self.assert_disallowed_methods_return_405()
