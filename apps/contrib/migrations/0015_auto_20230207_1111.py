# Generated by Django 3.0.14 on 2023-02-07 11:11

import apps.contrib.models
from django.db import migrations, models
import utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contrib', '0014_auto_20220823_0535'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='attachment',
            field=utils.fields.CachedFileField(max_length=2000, upload_to=apps.contrib.models.global_upload_to, verbose_name='Attachment'),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='filetype_detail',
            field=models.CharField(blank=True, max_length=2000, null=True, verbose_name='File type detail'),
        ),
        migrations.AlterField(
            model_name='exceldownload',
            name='file',
            field=utils.fields.CachedFileField(blank=True, max_length=2000, null=True, upload_to=apps.contrib.models.excel_upload_to, verbose_name='Excel File'),
        ),
        migrations.AlterField(
            model_name='sourcepreview',
            name='pdf',
            field=utils.fields.CachedFileField(blank=True, max_length=2000, null=True, upload_to=apps.contrib.models.global_upload_to, verbose_name='Rendered Pdf'),
        ),
    ]