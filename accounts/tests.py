from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase
from django.urls import reverse

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
