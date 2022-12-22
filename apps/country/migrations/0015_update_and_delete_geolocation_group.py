# Generated by Django 3.0.14 on 2022-12-22 05:26

from django.db import migrations


class Migration(migrations.Migration):

    def update_and_delete_duplicated_geographical_group(apps, schema_editor):
        GeographicalGroup = apps.get_model('country', 'GeographicalGroup')
        Country = apps.get_model('country', 'Country')

        location_to_keep = GeographicalGroup.objects.filter(name='Europe and Central Asia').first()
        location_to_delete = GeographicalGroup.objects.filter(name='Europe & Central Asia').first()

        if location_to_keep and location_to_delete:
            Country.objects.filter(
                geographical_group=location_to_delete
            ).update(
                geographical_group=location_to_keep
            )
            location_to_delete.delete()

    dependencies = [
        ('country', '0014_merge_20210702_0747'),
    ]

    operations = [
        migrations.RunPython(update_and_delete_duplicated_geographical_group),
    ]
