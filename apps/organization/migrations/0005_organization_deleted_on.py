# Generated by Django 3.0.5 on 2020-11-25 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0004_auto_20201111_1050'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='deleted_on',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
