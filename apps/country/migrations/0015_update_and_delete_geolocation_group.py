# Generated by Django 3.0.14 on 2022-12-22 05:26

from django.db import migrations


class Migration(migrations.Migration):

    def update_and_delete_duplicated_geographical_group(apps, schema_editor):
        GeographicalGroup = apps.get_model('country', 'GeographicalGroup')
        Country = apps.get_model('country', 'Country')
        ExtractionQuery = apps.get_model('extraction', 'ExtractionQuery')
        Report = apps.get_model('report', 'Report')

        location_to_keep = GeographicalGroup.objects.filter(name='Europe and Central Asia').first()
        location_to_delete = GeographicalGroup.objects.filter(name='Europe & Central Asia').first()

        if location_to_keep and location_to_delete:
            # Country
            Country.objects.filter(
                geographical_group=location_to_delete
            ).update(
                geographical_group=location_to_keep
            )

            # Extraction
            extractions = ExtractionQuery.objects.filter(
                filter_figure_geographical_groups=location_to_delete
            )
            for extraction in extractions:
                extraction.filter_figure_geographical_groups.add(location_to_keep)
                extraction.filter_figure_geographical_groups.remove(location_to_delete)

            # Report
            reports = Report.objects.filter(
                filter_figure_geographical_groups=location_to_delete
            )
            for report in reports:
                report.filter_figure_geographical_groups.add(location_to_keep)
                report.filter_figure_geographical_groups.remove(location_to_delete)

            # Finally remove geographical group
            location_to_delete.delete()

    dependencies = [
        ('extraction', '0035_extractionquery_filter_is_figure_to_be_reviewed'),
        ('report', '0045_report_filter_is_figure_to_be_reviewed'),
        ('country', '0014_merge_20210702_0747'),
    ]

    operations = [
        migrations.RunPython(update_and_delete_duplicated_geographical_group),
    ]
