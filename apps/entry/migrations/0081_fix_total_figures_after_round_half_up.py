# Generated by Django 3.0.14 on 2023-03-14 09:18

from django.db import migrations


class Migration(migrations.Migration):
    def fix_total_figures(apps, schema_editor):

        # Import util
        from utils.common import round_half_up

        # Import model
        Figure = apps.get_model('entry', 'Figure')

        for figure in Figure.objects.filter(
            household_size__isnull=False,
            reported__isnull=False,
            unit=1 # Figure.UNIT.HOUSEHOLD
        ):
            total_figures = round_half_up(figure.household_size * figure.reported)
            if figure.total_figures != total_figures:
                figure.total_figures = total_figures
                figure.save()

    dependencies = [
        ('entry', '0080_auto_20230216_0726'),
    ]

    operations = [
        migrations.RunPython(fix_total_figures, reverse_code=migrations.RunPython.noop),
    ]
