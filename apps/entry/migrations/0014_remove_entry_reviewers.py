# Generated by Django 3.0.5 on 2020-11-19 09:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0013_auto_20201119_0858'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='entry',
            name='reviewers',
        ),
    ]
