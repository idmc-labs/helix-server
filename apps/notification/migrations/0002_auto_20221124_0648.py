# Generated by Django 3.0.5 on 2022-11-24 06:48

import apps.notification.models
from django.db import migrations
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=django_enumfield.db.fields.EnumField(enum=apps.notification.models.Notification.Type),
        ),
    ]
