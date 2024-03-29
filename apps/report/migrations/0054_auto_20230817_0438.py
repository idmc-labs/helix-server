# Generated by Django 3.2 on 2023-08-17 04:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0053_auto_20230429_0842'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='gidd_published_date',
            field=models.DateTimeField(null=True, verbose_name='Date of data publication into the GIDD'),
        ),
        migrations.AddField(
            model_name='report',
            name='is_pfa_published_in_gidd',
            field=models.BooleanField(default=False, verbose_name='Is PFA published in GIDD'),
        ),
    ]
