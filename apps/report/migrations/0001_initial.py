# Generated by Django 3.0.5 on 2021-02-19 17:05

import apps.crisis.models
import apps.entry.models
from django.conf import settings
import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_enumfield.db.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('entry', '0034_figure_was_subfact'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crisis', '0003_auto_20210127_0845'),
        ('country', '0009_auto_20210204_0458'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_id', models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created At')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified At')),
                ('version_id', models.CharField(blank=True, max_length=16, null=True, verbose_name='Version')),
                ('displacement_urban', models.PositiveIntegerField(blank=True, null=True, verbose_name='Displacement/Urban')),
                ('displacement_rural', models.PositiveIntegerField(blank=True, null=True, verbose_name='Displacement/Rural')),
                ('location_camp', models.PositiveIntegerField(blank=True, null=True, verbose_name='Location/Camp')),
                ('location_non_camp', models.PositiveIntegerField(blank=True, null=True, verbose_name='Location/Non-Camp')),
                ('sex_male', models.PositiveIntegerField(blank=True, null=True, verbose_name='Sex/Male')),
                ('sex_female', models.PositiveIntegerField(blank=True, null=True, verbose_name='Sex/Female')),
                ('age_json', django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Age'), blank=True, null=True, size=None, verbose_name='Age Disaggregation')),
                ('strata_json', django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.jsonb.JSONField(verbose_name='Stratum'), blank=True, null=True, size=None, verbose_name='Strata Disaggregation')),
                ('conflict', models.PositiveIntegerField(blank=True, null=True, verbose_name='Conflict/Conflict')),
                ('conflict_political', models.PositiveIntegerField(blank=True, null=True, verbose_name='Conflict/Violence-Political')),
                ('conflict_criminal', models.PositiveIntegerField(blank=True, null=True, verbose_name='Conflict/Violence-Criminal')),
                ('conflict_communal', models.PositiveIntegerField(blank=True, null=True, verbose_name='Conflict/Violence-Communal')),
                ('conflict_other', models.PositiveIntegerField(blank=True, null=True, verbose_name='Other')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('figure_start_after', models.DateField(blank=True, null=True, verbose_name='From Date')),
                ('figure_end_before', models.DateField(blank=True, null=True, verbose_name='To Date')),
                ('figure_roles', django.contrib.postgres.fields.ArrayField(base_field=django_enumfield.db.fields.EnumField(enum=apps.entry.models.Figure.ROLE), blank=True, null=True, size=None)),
                ('entry_article_title', models.TextField(blank=True, null=True, verbose_name='Article Title')),
                ('event_crisis_type', django_enumfield.db.fields.EnumField(blank=True, enum=apps.crisis.models.Crisis.CRISIS_TYPE, null=True)),
                ('generated', models.BooleanField(default=True, editable=False, verbose_name='Generated')),
                ('analysis', models.TextField(blank=True, null=True, verbose_name='Analysis')),
                ('methodology', models.TextField(blank=True, null=True, verbose_name='Methodology')),
                ('significant_updates', models.TextField(blank=True, null=True, verbose_name='Significant Updates')),
                ('challenges', models.TextField(blank=True, null=True, verbose_name='Challenges')),
                ('reported', models.PositiveIntegerField(verbose_name='Reported Figures')),
                ('total_figures', models.PositiveIntegerField(default=0, editable=False, verbose_name='Total Figures')),
                ('summary', models.TextField(blank=True, help_text='It will store master fact information:Comment, Source Excerpt, IDU Excerpt, Breakdown & Reliability, and Caveats', null=True, verbose_name='Summary')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_report', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('entry_tags', models.ManyToManyField(blank=True, related_name='_report_entry_tags_+', to='entry.FigureTag', verbose_name='Figure Tags')),
                ('event_countries', models.ManyToManyField(blank=True, related_name='_report_event_countries_+', to='country.Country', verbose_name='Countries')),
                ('event_crises', models.ManyToManyField(blank=True, related_name='_report_event_crises_+', to='crisis.Crisis', verbose_name='Crises')),
                ('event_regions', models.ManyToManyField(blank=True, related_name='_report_event_regions_+', to='country.CountryRegion', verbose_name='Regions')),
                ('figure_categories', models.ManyToManyField(blank=True, related_name='_report_figure_categories_+', to='entry.FigureCategory', verbose_name='figure categories')),
                ('figures', models.ManyToManyField(blank=True, to='entry.Figure')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('reports', models.ManyToManyField(blank=True, related_name='_report_reports_+', to='report.Report', verbose_name='Reports (old groups)')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
