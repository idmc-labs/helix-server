# Generated by Django 3.0.5 on 2022-11-03 03:40

import apps.entry.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('entry', '0075_auto_20221101_0506'),
    ]

    operations = [
        migrations.AddField(
            model_name='figure',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='figure_approved_by', to=settings.AUTH_USER_MODEL, verbose_name='Approved by'),
        ),
        migrations.AddField(
            model_name='figure',
            name='approved_on',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Assigned at'),
        ),
        migrations.AddField(
            model_name='figure',
            name='review_status',
            field=django_enumfield.db.fields.EnumField(default=0, enum=apps.entry.models.Figure.FIGURE_REVIEW_STATUS),
        ),
    ]
