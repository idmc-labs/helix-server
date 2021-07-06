# Generated by Django 3.0.5 on 2021-07-06 11:24

import apps.entry.models
from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django_enumfield.db.fields
import utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('report', '0017_merge_20210512_1700'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='filter_entry_created_by',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='Entry Created by'),
        ),
        migrations.AddField(
            model_name='report',
            name='filter_event_glide_number',
            field=utils.fields.BleachedTextField(blank=True, null=True, verbose_name='Glide Number'),
        ),
        migrations.AddField(
            model_name='report',
            name='filter_figure_displacement_types',
            field=django.contrib.postgres.fields.ArrayField(base_field=django_enumfield.db.fields.EnumField(enum=apps.entry.models.FigureDisaggregationAbstractModel.DISPLACEMENT_TYPE), blank=True, null=True, size=None),
        ),
        migrations.AddField(
            model_name='report',
            name='filter_figure_sex_types',
            field=django.contrib.postgres.fields.ArrayField(base_field=django_enumfield.db.fields.EnumField(enum=apps.entry.models.FigureDisaggregationAbstractModel.GENDER_TYPE), blank=True, null=True, size=None),
        ),
    ]
