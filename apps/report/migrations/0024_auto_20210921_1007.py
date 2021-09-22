# Generated by Django 3.0.5 on 2021-09-21 10:07

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0023_report_filter_entry_has_review_comments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='filter_figure_category_types',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, choices=[('Stock', 'Stock'), ('Flow', 'Flow')], max_length=8, null=True, verbose_name='Type'), blank=True, null=True, size=None),
        ),
    ]
