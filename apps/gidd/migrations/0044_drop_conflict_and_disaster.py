import apps.crisis.models
import apps.entry.models
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('gidd', '0043_drop_displacementdata'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='disaster',
            name='country',
        ),
        migrations.RemoveField(
            model_name='disaster',
            name='event',
        ),
        migrations.RemoveField(
            model_name='disaster',
            name='hazard_category',
        ),
        migrations.RemoveField(
            model_name='disaster',
            name='hazard_sub_category',
        ),
        migrations.RemoveField(
            model_name='disaster',
            name='hazard_sub_type',
        ),
        migrations.RemoveField(
            model_name='disaster',
            name='hazard_type',
        ),
        migrations.DeleteModel(
            name='Conflict',
        ),
        migrations.DeleteModel(
            name='Disaster',
        ),
    ]
