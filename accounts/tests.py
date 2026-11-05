from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse, reverse_lazy
from PIL import Image

from .forms import CustomUserChangeForm, CustomUserCreationForm

User = get_user_model()
PASSWORD = 'pw-for-tests-1'


def make_user(username='reader', **fields):
    return User.objects.create_user(username, password=PASSWORD, **fields)


class UserModelTests(TestCase):
    """F602 accounts Model Class"""

    def test_user_inherits_abstract_user(self):
        self.assertTrue(issubclass(User, AbstractUser))

    def test_user_stores_all_required_fields(self):
        user = make_user(
            email='reader@example.com', last_name='김', first_name='독서',
            gender=User.Gender.FEMALE, age=25,
            weekly_reading_time=7, yearly_reading_count=30,
        )
        user.refresh_from_db()
        self.assertEqual(user.email, 'reader@example.com')
        self.assertEqual(user.last_name, '김')
        self.assertEqual(user.first_name, '독서')
        self.assertEqual(user.get_gender_display(), '여성')
        self.assertEqual(user.age, 25)
        self.assertEqual(user.weekly_reading_time, 7)
        self.assertEqual(user.yearly_reading_count, 30)
        self.assertFalse(user.profile_image)

    def test_follow_relation_is_many_to_many_and_one_directional(self):
        reader, writer = make_user('reader'), make_user('writer')
        reader.followings.add(writer)
        self.assertIn(reader, writer.followers.all())
        self.assertNotIn(reader, writer.followings.all())


class UserFormTests(TestCase):
    """F603 accounts Form Class"""

    def signup_data(self, **overrides):
        data = {
            'username': 'newbie', 'password1': 'long-enough-pw-1', 'password2': 'long-enough-pw-1',
            'email': 'newbie@example.com', 'last_name': '이', 'first_name': '새싹',
            'gender': User.Gender.MALE, 'age': 20,
            'weekly_reading_time': 3, 'yearly_reading_count': 12,
        }
        data.update(overrides)
        return data

    def test_creation_form_accepts_valid_data(self):
        self.assertTrue(CustomUserCreationForm(self.signup_data()).is_valid())

    def test_creation_form_rejects_password_mismatch(self):
        form = CustomUserCreationForm(self.signup_data(password2='different-pw-1'))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_creation_form_rejects_negative_numbers(self):
        form = CustomUserCreationForm(self.signup_data(age=-1))
        self.assertFalse(form.is_valid())
        self.assertIn('age', form.errors)

    def test_creation_form_hashes_password(self):
        user = CustomUserCreationForm(self.signup_data()).save()
        self.assertTrue(user.check_password('long-enough-pw-1'))

    def test_change_form_hides_sensitive_fields(self):
        form = CustomUserChangeForm(instance=make_user())
        for name in ('password', 'is_staff', 'is_superuser', 'is_active', 'groups', 'user_permissions', 'last_login'):
            self.assertNotIn(name, form.fields)

    def test_forms_apply_bootstrap_classes(self):
        form = CustomUserCreationForm()
        self.assertIn('form-control', form.fields['username'].widget.attrs['class'])
        self.assertIn('form-select', form.fields['gender'].widget.attrs['class'])


class LoginViewTests(TestCase):
    """F607 login"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.url = reverse('accounts:login')

    def test_get_renders_login_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_valid_credentials_create_session_and_redirect_to_main(self):
        response = self.client.post(self.url, {'username': 'reader', 'password': PASSWORD})
        self.assertRedirects(response, reverse('books:index'))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_invalid_credentials_show_error_without_session(self):
        response = self.client.post(self.url, {'username': 'reader', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alert-danger')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_authenticated_user_is_sent_to_main(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(self.url), reverse('books:index'))


class LogoutViewTests(TestCase):
    """F608 logout"""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.url = reverse('accounts:logout')

    def test_post_clears_session_and_redirects_to_main(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('books:index'))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_get_is_not_allowed_even_for_anonymous_user(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_logout_button_is_hidden_from_anonymous_user(self):
        self.assertNotContains(self.client.get(reverse('books:index')), self.url)


def png_upload(name='profile.png'):
    buffer = BytesIO()
    Image.new('RGB', (2, 2), 'green').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class SignupViewTests(TestCase):
    """F609 signup"""

    url = reverse_lazy('accounts:signup')

    def signup_data(self, **overrides):
        data = {
            'username': 'newbie', 'password1': 'long-enough-pw-1', 'password2': 'long-enough-pw-1',
            'email': 'newbie@example.com', 'last_name': '이', 'first_name': '새싹',
            'gender': User.Gender.MALE, 'age': 20,
            'weekly_reading_time': 3, 'yearly_reading_count': 12,
        }
        data.update(overrides)
        return data

    def test_get_renders_multipart_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_valid_data_creates_user_logs_in_and_redirects_to_main(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            response = self.client.post(self.url, self.signup_data(profile_image=png_upload()))
            self.assertRedirects(response, reverse('books:index'))
            user = User.objects.get(username='newbie')
            self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)
            self.assertEqual(user.yearly_reading_count, 12)
            self.assertTrue(user.profile_image.name.startswith('profiles/'))

    def test_invalid_data_shows_error_and_creates_nothing(self):
        response = self.client.post(self.url, self.signup_data(password2='different-pw-1'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'text-danger')
        self.assertFalse(User.objects.exists())

    def test_non_image_profile_file_is_rejected(self):
        fake = SimpleUploadedFile('profile.png', b'not an image', content_type='image/png')
        response = self.client.post(self.url, self.signup_data(profile_image=fake))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_authenticated_user_is_sent_to_main(self):
        self.client.force_login(make_user())
        self.assertRedirects(self.client.get(self.url), reverse('books:index'))
