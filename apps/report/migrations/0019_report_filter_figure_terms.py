# Generated by Django 3.0.5 on 2021-07-16 07:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0049_merge_20210702_1117'),
        ('report', '0018_auto_20210706_1124'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='filter_figure_terms',
            field=models.ManyToManyField(blank=True, to='entry.FigureTerm', verbose_name='Figure Term'),
        ),
    ]
