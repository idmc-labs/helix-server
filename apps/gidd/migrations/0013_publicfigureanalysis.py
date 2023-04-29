# Generated by Django 3.2 on 2023-04-26 05:08

import apps.crisis.models
import apps.entry.models
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0051_alter_report_gidd_report_year'),
        ('gidd', '0012_auto_20230425_1017'),
    ]

    operations = [
        migrations.CreateModel(
            name='PublicFigureAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iso3', models.CharField(max_length=5, verbose_name='ISO3')),
                ('figure_cause', django_enumfield.db.fields.EnumField(enum=apps.crisis.models.Crisis.CRISIS_TYPE)),
                ('figure_category', django_enumfield.db.fields.EnumField(enum=apps.entry.models.Figure.FIGURE_CATEGORY_TYPES)),
                ('year', models.IntegerField(verbose_name='Year')),
                ('figures', models.IntegerField(verbose_name='Figures')),
                ('description', models.TextField(verbose_name='Description')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='report.report', verbose_name='Report')),
            ],
        ),
    ]