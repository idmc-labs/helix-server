# Generated by Django 3.0.5 on 2021-02-22 11:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0034_figure_was_subfact'),
    ]

    operations = [
        migrations.AlterField(
            model_name='figure',
            name='start_date',
            field=models.DateField(null=True, verbose_name='Start Date'),
        ),
    ]
