# Generated by Django 3.0.5 on 2021-01-27 04:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('country', '0007_auto_20210105_0431'),
        ('contact', '0007_communication_attachment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='communication',
            name='date_time',
        ),
        migrations.AddField(
            model_name='communication',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='communications', to='country.Country', verbose_name='Country'),
        ),
        migrations.AddField(
            model_name='communication',
            name='date',
            field=models.DateField(blank=True, help_text='Date on which communication occurred.', null=True, verbose_name='Conducted Date'),
        ),
        migrations.AddField(
            model_name='contact',
            name='skype',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Skype'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contacts', to='organization.Organization', verbose_name='Organization'),
        ),
        migrations.AlterField(
            model_name='contact',
            name='phone',
            field=models.CharField(blank=True, max_length=256, null=True, unique=True, verbose_name='Phone'),
        ),
    ]
