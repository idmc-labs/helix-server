# Generated by Django 3.0.5 on 2021-10-21 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0031_auto_20211019_0701'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
    ]
