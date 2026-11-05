from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_safe, require_POST, require_http_methods
from django.core.exceptions import PermissionDenied

from .models import Book, Thread
from .forms import BookForm, ThreadForm


@require_safe
def index(request):
    books = Book.objects.select_related('user')

    context = {
        'books': books,
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
            return redirect('books:thread_detail', thread.pk)
    else:
        form = ThreadForm()

    context = {
        'form': form,
        'book': book,
    }
    return render(request, 'books/thread_create.html', context)


@require_safe
def thread_detail(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)

    context = {
        'thread': thread,
    }
    return render(request, 'books/thread_detail.html', context)


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


@login_required
@require_POST
def thread_delete(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)

    if request.user != thread.user:
        raise PermissionDenied

    book_pk = thread.book.pk
    thread.delete()
    return redirect('books:detail', book_pk)