from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hulk', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='hulkbulkimport',
            name='celery_task_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
