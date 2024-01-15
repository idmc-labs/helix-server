# Generated by Django 3.2 on 2024-01-13 15:22

import apps.contrib.models
from django.db import migrations, models
import utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contrib', '0029_bulkapioperation'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bulkapioperation',
            name='errors',
        ),
        migrations.AddField(
            model_name='bulkapioperation',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Completed At'),
        ),
        migrations.AddField(
            model_name='bulkapioperation',
            name='failure_list',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='bulkapioperation',
            name='snapshot',
            field=utils.fields.CachedFileField(blank=True, max_length=2000, null=True, upload_to=apps.contrib.models.bulk_operation_snapshot, verbose_name='Existing data snapshot'),
        ),
        migrations.AddField(
            model_name='bulkapioperation',
            name='started_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Started At'),
        ),
        migrations.AddField(
            model_name='bulkapioperation',
            name='success_list',
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name='bulkapioperation',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
    ]