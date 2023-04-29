# Generated by Django 3.2 on 2023-04-17 09:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0015_update_and_delete_geolocation_group'),
        ('gidd', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='disaster',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='country_disaster', to='country.country', verbose_name='Country'),
        ),
    ]