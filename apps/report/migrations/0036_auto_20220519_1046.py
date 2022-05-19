# Generated by Django 3.0.5 on 2022-05-19 10:46

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0035_auto_20220407_0651'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='filter_figure_category_types',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, choices=[('STOCK', 'STOCK'), ('FLOW', 'FLOW')], max_length=8, null=True, verbose_name='Type'), blank=True, null=True, size=None),
        ),
    ]
