# Generated by Django 3.0.5 on 2022-07-21 10:51

import apps.entry.models
from django.db import migrations, models
import utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0070_auto_20220617_0947'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalApiDump',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dump_file', utils.fields.CachedFileField(blank=True, null=True, upload_to=apps.entry.models.dump_file_upload_to, verbose_name='Dump file')),
                ('api_type', models.CharField(choices=[('idus', 'Idus')], max_length=40)),
                ('status', models.IntegerField(choices=[(0, 'Pending'), (1, 'Completed'), (2, 'Failed')], default=0)),
            ],
        ),
    ]
