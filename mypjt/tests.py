from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
