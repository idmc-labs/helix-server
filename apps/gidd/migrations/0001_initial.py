# Generated by Django 3.2 on 2023-04-17 09:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('event', '0031_fix_drought_and_cold_wave_data_migration'),
        ('country', '0015_update_and_delete_geolocation_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='Disaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.BigIntegerField()),
                ('country_name', models.CharField(blank=True, max_length=256, null=True, verbose_name='Name')),
                ('iso3', models.CharField(blank=True, max_length=5, null=True, verbose_name='ISO3')),
                ('start_date', models.DateField(blank=True, null=True)),
                ('start_date_accuracy', models.TextField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('end_date_accuracy', models.TextField(blank=True, null=True)),
                ('hazard_category', models.TextField(blank=True, null=True)),
                ('hazard_sub_category', models.TextField(blank=True, null=True)),
                ('hazard_sub_type', models.TextField(blank=True, null=True)),
                ('hazard_type', models.TextField(blank=True, null=True)),
                ('new_displacement', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='gidd_figures', to='event.event', verbose_name='Event')),
            ],
            options={
                'verbose_name': 'Disaster',
                'verbose_name_plural': 'Disasters',
            },
        ),
        migrations.CreateModel(
            name='Conflict',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_displacement', models.BigIntegerField(blank=True, null=True)),
                ('new_displacement', models.BigIntegerField(blank=True, null=True)),
                ('year', models.BigIntegerField()),
                ('country_name', models.CharField(blank=True, max_length=256, null=True, verbose_name='Name')),
                ('iso3', models.CharField(blank=True, max_length=5, null=True, verbose_name='ISO3')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='country_conflict', to='country.country', verbose_name='Country')),
            ],
            options={
                'verbose_name': 'Conflict',
                'verbose_name_plural': 'Conflicts',
            },
        ),
    ]
