import apps.crisis.models
import apps.entry.models
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('gidd', '0042_gidd_displacement_tables'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='displacementdata',
            name='country',
        ),
        migrations.DeleteModel(
            name='DisplacementData',
        ),
    ]
