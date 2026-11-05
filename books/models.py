from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Book(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='작성자',
    )
    title = models.CharField('도서 제목', max_length=200)
    description = models.TextField('설명')
    rating = models.FloatField(
        '회원 리뷰 평점',
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text='0 이상 10 이하로 입력합니다.',
    )
    author = models.CharField('저자', max_length=100)
    author_info = models.TextField('작가 정보', blank=True)
    author_works = models.TextField('작가 대표작', blank=True)
    author_image_url = models.URLField('작가 사진 URL', max_length=500, blank=True)

    class Meta:
        ordering = ['-pk']

    def __str__(self):
        return self.title


class Thread(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='작성자',
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='도서')
    title = models.CharField('제목', max_length=100)
    content = models.TextField('내용')
    reading_date = models.DateField('독서일')
    created_at = models.DateTimeField('생성 시각', auto_now_add=True)
    updated_at = models.DateTimeField('수정 시각', auto_now=True)
    like_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='like_threads',
        blank=True,
        verbose_name='좋아요한 사용자',
    )

    class Meta:
        ordering = ['-pk']

    def __str__(self):
        return self.title
