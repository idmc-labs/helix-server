# Generated by Django 3.0.5 on 2021-03-02 08:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('report', '0004_auto_20210226_0641'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='report',
            options={'permissions': (('sign_off_report', 'Can sign off the report'), ('approve_report', 'Can approve the report'))},
        ),
        migrations.AddField(
            model_name='report',
            name='is_signed_off',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='ReportSignOff',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_id', models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created At')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified At')),
                ('version_id', models.CharField(blank=True, max_length=16, null=True, verbose_name='Version')),
                ('full_report', utils.fields.CachedFileField(blank=True, null=True, upload_to='reports/full', verbose_name='full report')),
                ('snapshot', utils.fields.CachedFileField(blank=True, null=True, upload_to='reports/snaps', verbose_name='report snapshot')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_reportsignoff', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sign_offs', to='report.Report', verbose_name='Report')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ReportComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_id', models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created At')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified At')),
                ('version_id', models.CharField(blank=True, max_length=16, null=True, verbose_name='Version')),
                ('body', models.TextField(verbose_name='Body')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_reportcomment', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='report.Report', verbose_name='Report')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='ReportApproval',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_id', models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created At')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified At')),
                ('version_id', models.CharField(blank=True, max_length=16, null=True, verbose_name='Version')),
                ('is_approved', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approvals', to=settings.AUTH_USER_MODEL, verbose_name='Approved By')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approvals', to='report.Report', verbose_name='Report')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='report',
            name='approvers',
            field=models.ManyToManyField(related_name='approved_reports', through='report.ReportApproval', to=settings.AUTH_USER_MODEL, verbose_name='Approvers'),
        ),
    ]
