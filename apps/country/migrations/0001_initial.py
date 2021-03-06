# Generated by Django 3.0.5 on 2020-10-19 07:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, verbose_name='Name')),
            ],
        ),
        migrations.CreateModel(
            name='CountryRegion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256, verbose_name='Name')),
            ],
        ),
        migrations.CreateModel(
            name='Summary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created At')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified At')),
                ('version_id', models.CharField(blank=True, max_length=16, null=True, verbose_name='Version')),
                ('summary', models.TextField(verbose_name='Summary')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='summaries', to='country.Country', verbose_name='Country')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_summary', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='country',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='countries', to='country.CountryRegion', verbose_name='Region'),
        ),
        migrations.CreateModel(
            name='ContextualUpdate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created At')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified At')),
                ('version_id', models.CharField(blank=True, max_length=16, null=True, verbose_name='Version')),
                ('update', models.TextField(verbose_name='Update')),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contextual_updates', to='country.Country', verbose_name='Country')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_contextualupdate', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
