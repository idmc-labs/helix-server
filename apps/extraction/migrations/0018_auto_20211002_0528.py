# Generated by Django 3.0.5 on 2021-10-02 05:28

from django.db import migrations, models
import utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0054_auto_20210930_1312'),
        ('extraction', '0017_auto_20210921_1007'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='extractionquery',
            name='filter_entry_tags',
        ),
        migrations.AddField(
            model_name='extractionquery',
            name='filter_figure_tags',
            field=models.ManyToManyField(blank=True, related_name='_extractionquery_filter_figure_tags_+', to='entry.FigureTag', verbose_name='Figure Tags'),
        )
    ]