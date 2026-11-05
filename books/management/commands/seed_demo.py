"""관리자 계정과 샘플 데이터를 생성한다. 여러 번 실행해도 중복되지 않는다."""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from books.models import Book, Category, Comment, Thread

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '1234'
DEMO_PASSWORD = 'ssafy1234!'

DEMO_USERS = [
    {
        'username': 'alex', 'email': 'alex@example.com', 'last_name': '김', 'first_name': '알렉스',
        'gender': 'male', 'age': 28, 'weekly_reading_time': 6, 'yearly_reading_count': 24,
        'genres': ['소설/시/희곡', '인문/교양'],
    },
    {
        'username': 'sora', 'email': 'sora@example.com', 'last_name': '이', 'first_name': '소라',
        'gender': 'female', 'age': 31, 'weekly_reading_time': 10, 'yearly_reading_count': 40,
        'genres': ['과학', '자기계발'],
    },
]

DEMO_BOOKS = [
    {
        'owner': 'alex', 'title': '노인과 바다', 'author': '어니스트 헤밍웨이', 'rating': 8.5, 'category': '소설/시/희곡',
        'description': '늙은 어부 산티아고가 홀로 먼바다에 나가 거대한 청새치와 사투를 벌이는 이야기입니다.',
    },
    {
        'owner': 'sora', 'title': '코스모스', 'author': '칼 세이건', 'rating': 9.5, 'category': '과학',
        'description': '우주의 탄생과 생명의 기원, 인류가 걸어온 과학의 역사를 한 권에 담은 교양 과학서입니다.',
    },
    {
        'owner': 'alex', 'title': '사피엔스', 'author': '유발 하라리', 'rating': 8.8, 'category': '인문/교양',
        'description': '인지 혁명, 농업 혁명, 과학 혁명을 거치며 호모 사피엔스가 세계를 지배하게 된 과정을 살핍니다.',
    },
    {
        'owner': 'sora', 'title': '어린 왕자', 'author': '앙투안 드 생텍쥐페리', 'rating': 9.2, 'category': '어린이/청소년',
        'description': '사막에 불시착한 비행사가 작은 별에서 온 왕자를 만나 관계와 책임의 의미를 되새기는 이야기입니다.',
    },
    {
        'owner': 'sora', 'title': '아주 작은 습관의 힘', 'author': '제임스 클리어', 'rating': 8.2, 'category': '자기계발',
        'description': '사소한 행동의 반복이 어떻게 큰 변화를 만드는지 습관 형성의 원리를 설명합니다.',
    },
]

DEMO_THREADS = [
    {
        'owner': 'alex', 'book': '노인과 바다', 'title': '끝까지 포기하지 않는다는 것', 'reading_date': date(2026, 9, 20),
        'content': '결국 뼈만 남은 물고기를 끌고 돌아오는 노인의 모습이 오래 남았다.\n결과와 상관없이 끝까지 싸운 시간 자체가 그를 패배하지 않은 사람으로 만든다고 느꼈다.',
    },
    {
        'owner': 'sora', 'book': '코스모스', 'title': '창백한 푸른 점 앞에서', 'reading_date': date(2026, 10, 3),
        'content': '우주의 규모를 따라가다 보면 일상의 걱정이 작아지는 경험을 한다.\n그럼에도 그 작은 점 위에서 서로를 이해하려는 노력이 더 소중하게 느껴졌다.',
    },
]

DEMO_COMMENTS = [
    {'thread': '끝까지 포기하지 않는다는 것', 'owner': 'sora', 'content': '마지막 장면에 대한 해석에 공감합니다.'},
    {'thread': '창백한 푸른 점 앞에서', 'owner': 'alex', 'content': '저도 이 대목에서 한참 멈춰 있었어요.'},
]


class Command(BaseCommand):
    help = '관리자 계정(admin/1234)과 샘플 데이터를 생성합니다.'

    def handle(self, *args, **options):
        User = get_user_model()

        admin, created = User.objects.get_or_create(
            username=ADMIN_USERNAME,
            defaults={'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin.set_password(ADMIN_PASSWORD)
            admin.save()

        users = {}
        for data in DEMO_USERS:
            fields = {key: value for key, value in data.items() if key not in ('username', 'genres')}
            user, created = User.objects.get_or_create(username=data['username'], defaults=fields)
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                user.interested_genres.set(Category.objects.filter(name__in=data['genres']))
            users[data['username']] = user

        books = {}
        for data in DEMO_BOOKS:
            books[data['title']], _ = Book.objects.get_or_create(
                user=users[data['owner']],
                title=data['title'],
                defaults={
                    'author': data['author'],
                    'rating': data['rating'],
                    'description': data['description'],
                    'category': Category.objects.get(name=data['category']),
                },
            )

        threads = {}
        for data in DEMO_THREADS:
            threads[data['title']], _ = Thread.objects.get_or_create(
                user=users[data['owner']],
                book=books[data['book']],
                title=data['title'],
                defaults={'content': data['content'], 'reading_date': data['reading_date']},
            )

        for data in DEMO_COMMENTS:
            Comment.objects.get_or_create(
                thread=threads[data['thread']],
                user=users[data['owner']],
                content=data['content'],
            )

        users['alex'].followings.add(users['sora'])
        users['sora'].followings.add(users['alex'])
        threads['끝까지 포기하지 않는다는 것'].like_users.add(users['sora'])

        self.stdout.write(self.style.SUCCESS('샘플 데이터 준비 완료 (관리자: admin / 1234)'))
