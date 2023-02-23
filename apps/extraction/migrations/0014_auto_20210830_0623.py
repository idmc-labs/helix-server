# Generated by Django 3.0.5 on 2021-08-30 06:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0012_auto_20210526_0924'),
        ('extraction', '0013_extractionquery_filter_figure_terms'),
    ]

    operations = [
        migrations.AddField(
            model_name='extractionquery',
            name='filter_event_disaster_categories',
            field=models.ManyToManyField(blank=True, to='event.DisasterCategory', verbose_name='Hazard Category'),
        ),
        migrations.AddField(
            model_name='extractionquery',
            name='filter_event_disaster_sub_categories',
            field=models.ManyToManyField(blank=True, to='event.DisasterSubCategory', verbose_name='Hazard Sub Category'),
        ),
        migrations.AddField(
            model_name='extractionquery',
            name='filter_event_disaster_sub_types',
            field=models.ManyToManyField(blank=True, to='event.DisasterSubType', verbose_name='Hazard Sub Type'),
        ),
        migrations.AddField(
            model_name='extractionquery',
            name='filter_event_disaster_types',
            field=models.ManyToManyField(blank=True, to='event.DisasterType', verbose_name='Hazard Type'),
        ),
    ]
