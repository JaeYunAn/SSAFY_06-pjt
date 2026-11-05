from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AbstractUser
from django.test import TestCase
from django.urls import reverse

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
