# Generated by Django 3.0.5 on 2021-06-18 09:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0046_auto_20210527_1132'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='document_url',
            field=models.URLField(blank=True, max_length=2000, null=True, verbose_name='Document URL'),
        ),
    ]
