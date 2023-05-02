# Generated by Django 3.2 on 2023-05-02 06:28

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gidd', '0023_auto_20230501_1536'),
    ]

    operations = [
        migrations.AddField(
            model_name='disaster',
            name='glide_numbers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=256, verbose_name='Event Codes'), default=list, size=None),
        ),
    ]
