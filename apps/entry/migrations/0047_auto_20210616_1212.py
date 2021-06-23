# Generated by Django 3.0.5 on 2021-06-16 12:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contrib', '0009_exceldownload'),
        ('entry', '0046_auto_20210527_1132'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='preview',
            field=models.ForeignKey(blank=True, help_text='After the preview has been generated pass its id along during entry creation, so that during entry update the preview can be obtained.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entry', to='contrib.SourcePreview'),
        ),
    ]
