# Generated by Django 3.2 on 2023-10-20 09:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0055_update_new_gidd_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='report',
            name='filter_figure_displacement_types',
        ),
    ]
