import apps.crisis.models
import apps.entry.models
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0037_auto_20260817_0240'),
        ('country', '0024_country_search_trgm_idx'),
        ('gidd', '0041_unbleached_text_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='GiddDisplacement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iso3', models.CharField(max_length=5, verbose_name='ISO3')),
                ('country_name', models.CharField(max_length=256, verbose_name='Country name')),
                ('year', models.IntegerField()),
                ('cause', django_enumfield.db.fields.EnumField(enum=apps.crisis.models.Crisis.CRISIS_TYPE)),
                ('violence_name', models.CharField(blank=True, max_length=256, null=True)),
                ('violence_sub_type_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_category_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_sub_category_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_type_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_sub_type_name', models.CharField(blank=True, max_length=256, null=True)),
                ('new_displacement', models.BigIntegerField(blank=True, null=True)),
                ('new_displacement_rounded', models.BigIntegerField(blank=True, null=True)),
                ('total_displacement', models.BigIntegerField(blank=True, null=True)),
                ('total_displacement_rounded', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='gidd_displacements', to='country.country')),
                ('hazard_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event.disastercategory')),
                ('hazard_sub_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event.disastersubcategory')),
                ('hazard_sub_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event.disastersubtype')),
                ('hazard_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event.disastertype')),
                ('violence', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event.violence')),
                ('violence_sub_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event.violencesubtype')),
            ],
            options={
                'verbose_name': 'GIDD Disaggregated Displacement',
                'verbose_name_plural': 'GIDD Disaggregated Displacements',
            },
        ),
        migrations.CreateModel(
            name='GiddEventDisplacement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_raw_id', models.IntegerField(blank=True, null=True)),
                ('event_name', models.CharField(max_length=256, verbose_name='Event name')),
                ('iso3', models.CharField(max_length=5, verbose_name='ISO3')),
                ('country_name', models.CharField(max_length=256, verbose_name='Country name')),
                ('year', models.IntegerField()),
                ('cause', django_enumfield.db.fields.EnumField(enum=apps.crisis.models.Crisis.CRISIS_TYPE)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('event_codes', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=256, verbose_name='Event Codes'), default=list, size=None)),
                ('start_date_accuracy', models.TextField(blank=True, null=True)),
                ('end_date_accuracy', models.TextField(blank=True, null=True)),
                ('event_codes_type', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=256, verbose_name='Event Code Types'), default=list, size=None)),
                ('all_country_event_codes', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=256, verbose_name='Event Codes (all countries)'), default=list, size=None)),
                ('all_country_event_codes_type', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=256, verbose_name='Event Code Types (all countries)'), default=list, size=None)),
                ('displacement_occurred', django.contrib.postgres.fields.ArrayField(base_field=django_enumfield.db.fields.EnumField(enum=apps.entry.models.Figure.DISPLACEMENT_OCCURRED), default=list, size=None)),
                ('violence_name', models.CharField(blank=True, max_length=256, null=True)),
                ('violence_sub_type_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_category_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_sub_category_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_type_name', models.CharField(blank=True, max_length=256, null=True)),
                ('hazard_sub_type_name', models.CharField(blank=True, max_length=256, null=True)),
                ('new_displacement', models.BigIntegerField(blank=True, null=True)),
                ('new_displacement_rounded', models.BigIntegerField(blank=True, null=True)),
                ('total_displacement', models.BigIntegerField(blank=True, null=True)),
                ('total_displacement_rounded', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='gidd_event_displacements', to='country.country')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event.event')),
                ('hazard_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='event.disastercategory')),
                ('hazard_sub_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='event.disastersubcategory')),
                ('hazard_sub_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='event.disastersubtype')),
                ('hazard_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='event.disastertype')),
                ('violence', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='event.violence')),
                ('violence_sub_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='event.violencesubtype')),
            ],
            options={
                'verbose_name': 'GIDD Event Displacement',
                'verbose_name_plural': 'GIDD Event Displacements',
            },
        ),
    ]
