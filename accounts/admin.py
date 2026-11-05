from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('독서 정보', {
            'fields': (
                'gender', 'age', 'weekly_reading_time',
                'yearly_reading_count', 'profile_image', 'followings',
            ),
        }),
    )
    filter_horizontal = UserAdmin.filter_horizontal + ('followings',)
