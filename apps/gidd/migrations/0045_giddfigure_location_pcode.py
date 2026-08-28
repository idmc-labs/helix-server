import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gidd", "0044_drop_conflict_and_disaster"),
    ]

    operations = [
        migrations.AddField(
            model_name="giddfigure",
            name="locations_pcode",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=64, null=True, verbose_name="Location P-Code"),
                default=list,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="giddfigure",
            name="locations_pcode_accuracy",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.IntegerField(null=True, verbose_name="Location P-Code Accuracy"), default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="giddfigure",
            name="locations_pcode_source",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=256, null=True, verbose_name="Location P-Code Source"),
                default=list,
                size=None,
            ),
        ),
    ]
