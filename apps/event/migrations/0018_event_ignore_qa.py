# Generated by Django 3.0.5 on 2021-10-26 07:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0017_merge_20211008_0953'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='ignore_qa',
            field=models.BooleanField(default=False, verbose_name='Ignore QA'),
        ),
    ]
