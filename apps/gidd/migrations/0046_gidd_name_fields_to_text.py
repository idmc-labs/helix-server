import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gidd", "0045_giddfigure_location_pcode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="giddevent",
            name="event_codes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Event Codes"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddevent",
            name="event_codes_iso3",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Event Code ISO3"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddevent",
            name="name",
            field=models.TextField(verbose_name="Event Name"),
        ),
        migrations.AlterField(
            model_name="giddeventdisplacement",
            name="all_country_event_codes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Event Codes (all countries)"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddeventdisplacement",
            name="all_country_event_codes_type",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Event Code Types (all countries)"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddeventdisplacement",
            name="event_codes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Event Codes"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddeventdisplacement",
            name="event_codes_type",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Event Code Types"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddeventdisplacement",
            name="event_name",
            field=models.TextField(verbose_name="Event name"),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="entry_name",
            field=models.TextField(blank=True, null=True, verbose_name="Entry Title"),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="locations_coordinates",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Location Coordinates"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="locations_names",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Location Names"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="locations_pcode",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(null=True, verbose_name="Location P-Code"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="locations_pcode_source",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(null=True, verbose_name="Location P-Code Source"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="publishers",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Publishers"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="publishers_type",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Publishers Type"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="sources",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Sources"), default=list, size=None
            ),
        ),
        migrations.AlterField(
            model_name="giddfigure",
            name="sources_type",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(verbose_name="Sources Type"), default=list, size=None
            ),
        ),
    ]
