from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .forms import CustomUserChangeForm, CustomUserCreationForm, LoginForm

User = get_user_model()


@require_http_methods(['GET', 'POST'])
def login(request):
    if request.user.is_authenticated:
        return redirect('books:index')

    if request.method == 'POST':
        form = LoginForm(request, request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect('books:index')
    else:
        form = LoginForm()

    context = {
        'form': form,
    }
    return render(request, 'accounts/login.html', context)


@require_POST
@login_required
def logout(request):
    auth_logout(request)
    return redirect('books:index')


@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('books:index')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('books:index')
    else:
        form = CustomUserCreationForm()

    context = {
        'form': form,
    }
    return render(request, 'accounts/signup.html', context)


@require_safe
def profile(request, username):
    person = get_object_or_404(User, username=username)

    context = {
        'person': person,
        'threads': person.thread_set.select_related('book'),
        'is_following': person.followers.filter(pk=request.user.pk).exists(),
    }
    return render(request, 'accounts/profile.html', context)


@require_POST
@login_required
def follow(request, username):
    person = get_object_or_404(User, username=username)

    if person != request.user:
        if person.followers.filter(pk=request.user.pk).exists():
            person.followers.remove(request.user)
        else:
            person.followers.add(request.user)

    return redirect('accounts:profile', person.username)


@login_required
@require_http_methods(['GET', 'POST'])
def update(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(
            request.POST,
            request.FILES,
            instance=request.user
        )
        if form.is_valid():
            form.save()
            return redirect('books:index')
        # 검증 과정에서 변경된 메모리 값이 Navbar 등에 노출되지 않도록 되돌린다.
        request.user.refresh_from_db()
    else:
        form = CustomUserChangeForm(instance=request.user)

    context = {
        'form': form,
    }
    return render(request, 'accounts/update.html', context)


@login_required
@require_POST
def delete(request):
    request.user.delete()
    auth_logout(request)
    return redirect('books:index')


@login_required
@require_http_methods(['GET', 'POST'])
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('accounts:profile', request.user.username)
    else:
        form = PasswordChangeForm(request.user)

    context = {
        'form': form,
    }
    return render(request, 'accounts/change_password.html', context)