from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from mypjt.forms import BootstrapFormMixin

User = get_user_model()


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class CustomPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class CustomUserCreationForm(BootstrapFormMixin, UserCreationForm):
    field_order = (
        'username', 'password1', 'password2', 'email', 'last_name', 'first_name',
        'gender', 'age', 'weekly_reading_time', 'yearly_reading_count', 'profile_image',
        'interested_genres',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username', 'email', 'last_name', 'first_name',
            'gender', 'age', 'weekly_reading_time',
            'yearly_reading_count', 'profile_image', 'interested_genres',
        )
        labels = {'username': '아이디'}
        widgets = {'interested_genres': forms.CheckboxSelectMultiple}


class CustomUserChangeForm(BootstrapFormMixin, UserChangeForm):
    # 비밀번호 해시와 권한 필드는 일반 사용자에게 노출하지 않는다.
    password = None

    class Meta(UserChangeForm.Meta):
        model = User
        fields = (
            'username', 'last_name', 'first_name', 'email',
            'gender', 'age', 'weekly_reading_time',
            'yearly_reading_count', 'profile_image', 'interested_genres',
        )
        labels = {'username': '아이디'}
        widgets = {'interested_genres': forms.CheckboxSelectMultiple}
