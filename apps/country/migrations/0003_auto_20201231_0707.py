# Generated by Django 3.0.5 on 2020-12-31 07:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0002_auto_20201105_0537'),
    ]

    operations = [
        migrations.AddField(
            model_name='contextualupdate',
            name='old_id',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key'),
        ),
        migrations.AddField(
            model_name='summary',
            name='old_id',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key'),
        ),
    ]
