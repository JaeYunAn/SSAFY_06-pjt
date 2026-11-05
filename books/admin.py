from django.contrib import admin

from .models import Book, Comment, Thread


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'rating', 'user')
    search_fields = ('title', 'author')


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'user', 'reading_date', 'created_at')
    search_fields = ('title', 'content')
    filter_horizontal = ('like_users',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('content', 'thread', 'user', 'created_at')
