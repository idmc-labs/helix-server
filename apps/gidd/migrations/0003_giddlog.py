# Generated by Django 3.2 on 2023-04-19 07:15

import apps.gidd.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gidd', '0002_disaster_country'),
    ]

    operations = [
        migrations.CreateModel(
            name='GiddLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('triggered_at', models.DateTimeField(auto_now_add=True, verbose_name='Triggered at')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Completed at')),
                ('status', django_enumfield.db.fields.EnumField(default=0, enum=apps.gidd.models.StatusLog.Status)),
                ('triggered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gidd_data_triggered_by', to=settings.AUTH_USER_MODEL, verbose_name='Triggered by')),
            ],
            options={
                'permissions': (('update_gidd_data', 'Can update gidd data'),),
            },
        ),
    ]
