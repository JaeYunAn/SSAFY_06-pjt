from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Gender(models.TextChoices):
        MALE = 'male', '남성'
        FEMALE = 'female', '여성'

    gender = models.CharField('성별', max_length=10, choices=Gender.choices, blank=True)
    age = models.PositiveIntegerField('나이', null=True, blank=True)
    weekly_reading_time = models.PositiveIntegerField('주간 평균 독서 시간(시간)', default=0)
    yearly_reading_count = models.PositiveIntegerField('연간 독서량(권)', default=0)
    profile_image = models.ImageField('프로필 사진', upload_to='profiles/', blank=True)
    followings = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='followers',
        blank=True,
        verbose_name='팔로잉',
    )
