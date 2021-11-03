# Generated by Django 3.0.5 on 2021-11-03 02:32

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0034_remove_report_filter_figure_sex_types'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='report',
            name='filter_event_glide_number',
        ),
        migrations.AddField(
            model_name='report',
            name='filter_event_name_or_code',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100, null=True, verbose_name='Event Name / Code'), blank=True, null=True, size=None),
        ),
    ]
