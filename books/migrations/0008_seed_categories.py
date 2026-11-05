from django.db import migrations

GENRES = ['소설/시/희곡', '경제/경영', '자기계발', '인문/교양', '취미/실용', '어린이/청소년', '과학']


def create_genres(apps, schema_editor):
    Category = apps.get_model('books', 'Category')
    for name in GENRES:
        Category.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0007_category'),
    ]

    operations = [
        migrations.RunPython(create_genres, migrations.RunPython.noop),
    ]
