# Generated by Django 3.0.5 on 2022-06-13 09:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0039_auto_20220601_1334'),
    ]

    operations = [
        migrations.RenameField(
            model_name='report',
            old_name='filter_entry_sources',
            new_name='filter_figure_sources',
        ),
    ]