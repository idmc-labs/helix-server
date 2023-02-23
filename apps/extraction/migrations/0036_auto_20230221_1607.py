# Generated by Django 3.0.14 on 2023-02-21 16:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0030_auto_20230216_0726'),
        ('extraction', '0035_extractionquery_filter_is_figure_to_be_reviewed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extractionquery',
            name='filter_figure_disaster_categories',
            field=models.ManyToManyField(blank=True, to='event.DisasterCategory', verbose_name='Hazard Category'),
        ),
        migrations.AlterField(
            model_name='extractionquery',
            name='filter_figure_disaster_sub_categories',
            field=models.ManyToManyField(blank=True, to='event.DisasterSubCategory', verbose_name='Hazard Sub Category'),
        ),
        migrations.AlterField(
            model_name='extractionquery',
            name='filter_figure_disaster_sub_types',
            field=models.ManyToManyField(blank=True, to='event.DisasterSubType', verbose_name='Hazard Sub Type'),
        ),
        migrations.AlterField(
            model_name='extractionquery',
            name='filter_figure_disaster_types',
            field=models.ManyToManyField(blank=True, to='event.DisasterType', verbose_name='Hazard Type'),
        ),
    ]
