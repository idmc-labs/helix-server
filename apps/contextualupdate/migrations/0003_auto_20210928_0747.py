# Generated by Django 3.0.5 on 2021-09-28 07:47

from django.db import migrations
import utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contextualupdate', '0002_auto_20210323_0857'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contextualupdate',
            name='article_title',
            field=utils.fields.BleachedTextField(verbose_name='Event Title'),
        ),
    ]
