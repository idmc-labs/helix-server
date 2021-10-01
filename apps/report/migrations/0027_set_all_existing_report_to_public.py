from django.db import migrations


def set_all_report_to_public(apps, schema_editor):

    Report = apps.get_model("report", "Report")
    Report.objects.all().update(is_public=True)

class Migration(migrations.Migration):

    dependencies = [("report", "0026_auto_20211001_0530")]

    operations = [migrations.RunPython(set_all_report_to_public)]
