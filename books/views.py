from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_safe, require_POST, require_http_methods
from django.core.exceptions import PermissionDenied

from . import services
from .models import Book, Category, Comment, Thread
from .forms import BookForm, CommentForm, ThreadForm

AUTHOR_INFO_FAILED_MESSAGE = '작가 정보를 불러오지 못했습니다. 도서는 정상적으로 저장되었습니다.'
COVER_FAILED_MESSAGE = '커버 이미지를 생성하지 못했습니다. 쓰레드는 정상적으로 저장되었습니다.'


@require_safe
def index(request):
    books = Book.objects.select_related('user', 'category')
    categories = Category.objects.all()

    # 잘못된 쿼리 값은 필터 없이 전체 목록으로 처리한다.
    selected_category = None
    category_pk = request.GET.get('category', '')
    if category_pk.isdecimal():
        selected_category = categories.filter(pk=category_pk).first()
    if selected_category:
        books = books.filter(category=selected_category)

    context = {
        'books': books,
        'categories': categories,
        'selected_category': selected_category,
    }
    return render(request, 'books/index.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def create(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.user = request.user
            book.save()
            if not services.update_author_info(book):
                messages.warning(request, AUTHOR_INFO_FAILED_MESSAGE)
            return redirect('books:detail', book.pk)
    else:
        form = BookForm()

    context = {
        'form': form,
    }
    return render(request, 'books/create.html', context)


@require_safe
def detail(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)
    threads = book.thread_set.select_related('user')

    context = {
        'book': book,
        'threads': threads,
    }
    return render(request, 'books/detail.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def update(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)

    if request.user != book.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            # 저자가 바뀌면 이전 저자의 정보가 남지 않도록 다시 생성한다.
            if 'author' in form.changed_data and not services.update_author_info(book):
                messages.warning(request, AUTHOR_INFO_FAILED_MESSAGE)
            return redirect('books:detail', book.pk)
    else:
        form = BookForm(instance=book)

    context = {
        'form': form,
        'book': book,
    }
    return render(request, 'books/update.html', context)


@require_POST
@login_required
def delete(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)

    if request.user != book.user:
        raise PermissionDenied

    book.delete()
    return redirect('books:index')


@login_required
@require_http_methods(['GET', 'POST'])
def thread_create(request, book_pk):
    book = get_object_or_404(Book, pk=book_pk)

    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.user = request.user
            thread.book = book
            thread.save()
            if not services.generate_thread_cover(thread):
                messages.warning(request, COVER_FAILED_MESSAGE)
            return redirect('books:thread_detail', thread.pk)
    else:
        form = ThreadForm()

    context = {
        'form': form,
        'book': book,
    }
    return render(request, 'books/thread_create.html', context)


def render_thread_detail(request, thread, comment_form=None):
    context = {
        'thread': thread,
        'is_liked': thread.like_users.filter(pk=request.user.pk).exists(),
        'comments': thread.comment_set.select_related('user'),
        'comment_form': comment_form or CommentForm(),
    }
    return render(request, 'books/thread_detail.html', context)


@require_safe
def thread_detail(request, thread_pk):
    thread = get_object_or_404(Thread.objects.select_related('book', 'user'), pk=thread_pk)
    return render_thread_detail(request, thread)


@login_required
@require_http_methods(['GET', 'POST'])
def thread_update(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)

    if request.user != thread.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = ThreadForm(request.POST, instance=thread)
        if form.is_valid():
            form.save()
            return redirect('books:thread_detail', thread.pk)
    else:
        form = ThreadForm(instance=thread)

    context = {
        'form': form,
        'thread': thread,
    }
    return render(request, 'books/thread_update.html', context)


@require_POST
@login_required
def thread_delete(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)

    if request.user != thread.user:
        raise PermissionDenied

    book_pk = thread.book_id
    thread.delete()
    return redirect('books:detail', book_pk)


@require_POST
@login_required
def like(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)

    if thread.like_users.filter(pk=request.user.pk).exists():
        thread.like_users.remove(request.user)
    else:
        thread.like_users.add(request.user)

    return redirect('books:thread_detail', thread.pk)


@require_POST
@login_required
def comment_create(request, thread_pk):
    thread = get_object_or_404(Thread.objects.select_related('book', 'user'), pk=thread_pk)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.thread = thread
        comment.user = request.user
        comment.save()
        return redirect('books:thread_detail', thread.pk)

    return render_thread_detail(request, thread, form)


@require_POST
@login_required
def comment_delete(request, thread_pk, comment_pk):
    comment = get_object_or_404(Comment, pk=comment_pk, thread_id=thread_pk)

    if request.user != comment.user:
        raise PermissionDenied

    comment.delete()
    return redirect('books:thread_detail', thread_pk)
