# Generated by Django 3.0.5 on 2022-10-13 09:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0041_auto_20220704_0110'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='report',
            name='filter_entry_has_review_comments',
        ),
        migrations.RemoveField(
            model_name='report',
            name='filter_entry_review_status',
        ),
    ]
