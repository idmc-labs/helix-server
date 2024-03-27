# Generated by Django 3.2 on 2024-03-26 08:24

import apps.contrib.models
from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contrib', '0030_auto_20240113_1522'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='acronym',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Client Acronym'),
        ),
        migrations.AddField(
            model_name='client',
            name='contact_email',
            field=models.EmailField(blank=True, help_text='Client Contact Email: email focal person', max_length=254, null=True, verbose_name='Client Contact Email'),
        ),
        migrations.AddField(
            model_name='client',
            name='contact_name',
            field=models.CharField(blank=True, help_text='Client Contact Name: focal person', max_length=255, null=True, verbose_name='Client Contact Name'),
        ),
        migrations.AddField(
            model_name='client',
            name='contact_website',
            field=models.URLField(blank=True, help_text='Client Contact Website: link to the website (IDMC application)', null=True, verbose_name='Client Contact Website'),
        ),
        migrations.AddField(
            model_name='client',
            name='date_expiration',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='opted_out_of_emails',
            field=models.BooleanField(default=False, verbose_name='Opted out of receiving emails'),
        ),
        migrations.AddField(
            model_name='client',
            name='other_notes',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='client',
            name='revoked_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Revoked At'),
        ),
        migrations.AddField(
            model_name='client',
            name='revoked_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='clients_revoked', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='client',
            name='use_case',
            field=django.contrib.postgres.fields.ArrayField(base_field=django_enumfield.db.fields.EnumField(enum=apps.contrib.models.Client.USE_CASE_CHOICES), blank=True, default=list, size=None),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
        migrations.AlterField(
            model_name='client',
            name='code',
            field=models.CharField(editable=False, max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='client',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
        migrations.AlterField(
            model_name='exceldownload',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
        migrations.AlterField(
            model_name='sourcepreview',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Created At'),
        ),
    ]
