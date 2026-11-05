from django import forms
from .models import Book, Thread


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ('title', 'description', 'rating', 'author')


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ('title', 'content', 'reading_date')
        widgets = {
            'reading_date': forms.DateInput(
                attrs={'type': 'date'}
            ),
        }