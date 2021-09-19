# Generated by Django 3.0.5 on 2021-08-24 04:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0051_auto_20210726_0611'),
    ]

    operations = [
        migrations.AddField(
            model_name='figure',
            name='disaggregation_disability',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Disability'),
        ),
        migrations.AddField(
            model_name='figure',
            name='disaggregation_indigenous_people',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Indigenous people'),
        ),
        migrations.AddField(
            model_name='figure',
            name='disaggregation_lgbtiq',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='LGBTIQ+'),
        ),
    ]
