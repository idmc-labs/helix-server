# Generated by Django 3.0.5 on 2021-01-21 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contrib', '0003_auto_20210120_1001'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachment',
            name='encoding',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Encoding'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='filetype_detail',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='File type detail'),
        ),
        migrations.AddField(
            model_name='attachment',
            name='mimetype',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Mimetype'),
        ),
    ]
