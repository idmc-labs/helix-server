# Generated by Django 3.0.5 on 2022-11-30 13:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0043_report_filter_figure_review_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='report',
            old_name='filter_entry_created_by',
            new_name='filter_created_by',
        ),
        migrations.RenameField(
            model_name='report',
            old_name='filter_events',
            new_name='filter_figure_events',
        ),
    ]
