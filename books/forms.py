from django import forms

from mypjt.forms import BootstrapFormMixin

from .models import Book, Comment, Thread


class BookForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Book
        fields = ('title', 'description', 'rating', 'author', 'category')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
            'rating': forms.NumberInput(attrs={'min': 0, 'max': 10, 'step': 0.1}),
        }


class ThreadForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Thread
        fields = ('title', 'content', 'reading_date')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 8}),
            # type="date" 입력은 ISO 형식 값만 미리 채울 수 있다.
            'reading_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }


class CommentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)
