# Generated by Django 3.0.5 on 2020-12-31 07:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contact', '0004_auto_20201111_0851'),
    ]

    operations = [
        migrations.AddField(
            model_name='communication',
            name='old_id',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key'),
        ),
        migrations.AddField(
            model_name='contact',
            name='old_id',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key'),
        ),
    ]
