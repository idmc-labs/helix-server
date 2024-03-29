# Generated by Django 3.0.5 on 2022-06-17 09:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0069_auto_20220613_0548'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='disaggregatedage',
            name='category',
        ),
        migrations.AddField(
            model_name='disaggregatedage',
            name='age_from',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Age From'),
        ),
        migrations.AddField(
            model_name='disaggregatedage',
            name='age_to',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Age To'),
        ),
        migrations.DeleteModel(
            name='DisaggregatedAgeCategory',
        ),
    ]
