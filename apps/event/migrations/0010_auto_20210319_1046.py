# Generated by Django 3.0.5 on 2021-03-19 10:46

import apps.contrib.commons
from django.db import migrations
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0009_auto_20210202_0517'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='end_date_accuracy',
            field=django_enumfield.db.fields.EnumField(default=0, enum=apps.contrib.commons.DATE_ACCURACY),
        ),
        migrations.AddField(
            model_name='event',
            name='start_date_accuracy',
            field=django_enumfield.db.fields.EnumField(default=0, enum=apps.contrib.commons.DATE_ACCURACY),
        ),
    ]
