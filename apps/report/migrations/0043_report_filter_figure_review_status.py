# Generated by Django 3.0.5 on 2022-11-03 12:00

import apps.entry.models
import django.contrib.postgres.fields
from django.db import migrations
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0042_auto_20221028_0521'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='filter_figure_review_status',
            field=django.contrib.postgres.fields.ArrayField(base_field=django_enumfield.db.fields.EnumField(enum=apps.entry.models.Figure.FIGURE_REVIEW_STATUS), blank=True, null=True, size=None),
        ),
    ]