from django.db import models

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    gender = models.CharField(max_length=10, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    weekly_reading_time = models.PositiveIntegerField(default=0)
    yearly_reading_count = models.PositiveIntegerField(default=0)
    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True
    )
    followings = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='followers',
        blank=True
    )