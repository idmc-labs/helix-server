# Generated by Django 3.0.5 on 2022-10-13 09:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('event', '0021_auto_20220530_1013'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='assigned_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Assigned at'),
        ),
        migrations.AddField(
            model_name='event',
            name='assignee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='event_assignee', to=settings.AUTH_USER_MODEL, verbose_name='Assignee'),
        ),
        migrations.AddField(
            model_name='event',
            name='reviewer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='event_reviewer', to=settings.AUTH_USER_MODEL, verbose_name='Reviewer'),
        ),
    ]
