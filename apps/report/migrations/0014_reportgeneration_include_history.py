# Generated by Django 3.0.5 on 2021-03-16 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0013_auto_20210316_0530'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportgeneration',
            name='include_history',
            field=models.BooleanField(default=False, help_text='Including history will take good amount of time.', verbose_name='Include History'),
        ),
    ]
