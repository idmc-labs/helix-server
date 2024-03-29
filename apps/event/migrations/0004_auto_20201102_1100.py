# Generated by Django 3.0.5 on 2020-11-02 11:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0003_remove_triggersubtype_trigger'),
    ]

    operations = [
        migrations.AlterField(
            model_name='disastersubtype',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sub_types', to='event.DisasterType', verbose_name='Hazard Type'),
        ),
    ]
