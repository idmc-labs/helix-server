# Generated by Django 3.2 on 2023-05-26 05:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contrib', '0025_update_existing_client_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clienttrackinfo',
            name='api_type',
            field=models.CharField(choices=[('idus', 'HELIX idus last 180 days'), ('idus-all', 'HELIX idus all'), ('idus-all-disaster', 'HELIX idus all disasters'), ('gidd-country-rest', 'GIDD countries'), ('gidd-conflict-rest', 'GIDD conflicts'), ('gidd-disaster-rest', 'GIDD disasters'), ('gidd-displacement-rest', 'GIDD displacements'), ('gidd-disaster-export-rest', 'GIDD disasters export'), ('gidd-displacement-export-rest', 'GIDD displacements export'), ('gidd-public-figure-analysis-rest', 'GIDD public figure analyses'), ('gidd-conflict-graphql', 'GIDD conflicts [graphql]'), ('gidd-disaster-graphql', 'GIDD disasters [graphql]'), ('gidd-displacement-data-graphql', 'GIDD displacements [graphql]'), ('gidd-public-figure-analysis-graphql', 'GIDD public figure analyses [graphql]'), ('gidd-conflict-stat-graphql', 'GIDD conflict statistics [graphql]'), ('gidd-disaster-stat-graphql', 'GIDD disaster statistics [graphql]'), ('gidd-hazard-type-graphql', 'GIDD hazard types [graphql]'), ('gidd-year-graphql', 'GIDD year [graphql]'), ('gidd-event-graphql', 'GIDD event [graphql]'), ('gidd-combined-stat-graphql', 'GIDD combined statistics [graphql]'), ('gidd-release-meta-data-graphql', 'GIDD release metadata [graphql]'), ('gidd-public-countries-graphql', 'GIDD public countries [graphql]')], max_length=40),
        ),
    ]
