# Generated by Django 3.0.5 on 2021-05-26 09:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0011_auto_20210330_0905'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='violence',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='event.Violence', verbose_name='Violence'),
        ),
    ]
