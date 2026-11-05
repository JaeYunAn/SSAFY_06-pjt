from django.contrib import admin

from .models import Book, Category, Comment, Thread


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'rating', 'user')
    list_filter = ('category',)
    search_fields = ('title', 'author')


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'book', 'user', 'reading_date', 'created_at')
    search_fields = ('title', 'content')
    filter_horizontal = ('like_users',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('content', 'thread', 'user', 'created_at')
