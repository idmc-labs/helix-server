# Generated by Django 3.0.5 on 2021-10-09 05:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0029_auto_20211008_1407'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='filter_entry_article_title',
            field=models.TextField(blank=True, null=True, verbose_name='Event Title'),
        ),
    ]