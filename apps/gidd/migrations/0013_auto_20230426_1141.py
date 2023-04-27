# Generated by Django 3.2 on 2023-04-26 11:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0016_update_idmc_short_names'),
        ('gidd', '0012_auto_20230425_1017'),
    ]

    operations = [
        migrations.AddField(
            model_name='disaster',
            name='total_displacement',
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='DisplacementData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iso3', models.CharField(max_length=5, verbose_name='ISO3')),
                ('country_name', models.CharField(max_length=256, verbose_name='Country name')),
                ('conflict_total_displacement', models.BigIntegerField(verbose_name='Conflict total displacement')),
                ('disaster_total_displacement', models.BigIntegerField(verbose_name='Disaster total displacement')),
                ('conflict_new_displacement', models.BigIntegerField(verbose_name='Conflict new displacement')),
                ('disaster_new_displacement', models.BigIntegerField(verbose_name='Disaster new displacement')),
                ('total_internal_displacement', models.BigIntegerField(verbose_name='Total internal displacement')),
                ('total_new_displacement', models.BigIntegerField(verbose_name='Total new displacement')),
                ('year', models.IntegerField(verbose_name='Year')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='displacements', to='country.country', verbose_name='Country')),
            ],
        ),
    ]
