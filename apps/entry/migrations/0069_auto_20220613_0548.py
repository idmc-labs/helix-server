# Generated by Django 3.0.5 on 2022-06-13 05:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0007_auto_20210623_0357'),
        ('entry', '0068_remove_figure_caveats'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='entry',
            name='sources',
        ),
        migrations.AddField(
            model_name='figure',
            name='sources',
            field=models.ManyToManyField(blank=True, related_name='sourced_figures', to='organization.Organization', verbose_name='Source'),
        ),
    ]
