# Generated by Django 3.2 on 2023-04-29 08:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contrib', '0017_alter_clienttrackinfo_api_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clienttrackinfo',
            name='api_type',
            field=models.CharField(choices=[('idus', 'Idus'), ('idus-all', 'Idus all'), ('idus-all-disaster', 'Idus all disaster'), ('gidd-countries-disaster-export-rest', 'Countries disaster export REST'), ('gidd-conflict-export-rest', 'Conflict export REST'), ('gidd-disaster-export-rest', 'Disaster export REST'), ('gidd-conflict', 'GIDD conflict'), ('gidd-disaster', 'GIDD disaster'), ('gidd-conflict-stat', 'GIDD conflict stat'), ('gidd-disaster-stat', 'GIDD disaster stat')], max_length=40),
        ),
    ]