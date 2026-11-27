from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gidd", "0046_gidd_name_fields_to_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="giddevent",
            name="hazard_intensity_value",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="giddevent",
            name="hazard_intensity_unit",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="giddevent",
            name="hazard_source_name",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name="giddevent",
            name="hazard_footprint_url",
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name="giddevent",
            name="hazard_footprint_id",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name="giddevent",
            name="hazard_footprint_geometry_type",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="giddeventdisplacement",
            name="hazard_intensity_value",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="giddeventdisplacement",
            name="hazard_intensity_unit",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="giddeventdisplacement",
            name="hazard_source_name",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name="giddeventdisplacement",
            name="hazard_footprint_url",
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.AddField(
            model_name="giddeventdisplacement",
            name="hazard_footprint_id",
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name="giddeventdisplacement",
            name="hazard_footprint_geometry_type",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
