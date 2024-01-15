from django.db import migrations
from django.conf import settings


def migrate_data(Event, Figure, Violence, ViolenceSubType):
    # Migrate violence sub type to "International armed conflict(IAC)"
    violence_sub_type_military = ViolenceSubType.objects.get(name='Military Occupation')
    violence_sub_type_military.name = 'International armed conflict(IAC)'
    violence_sub_type_military.save()

    new_violence_sub_type = violence_sub_type_military

    # Migrate Event violence sub type other than "Military" to "International armed conflicts(IAC)"
    violence_sub_type_to_delete = ViolenceSubType.objects.filter(
        name__in=[
            'IAC (other than occupation)',
            'Other (IAC)',
            'Unclear (IAC)',
            'Unknown (IAC)',
        ]
    )

    Event.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    Figure.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    # Delete violence sub types to delete
    violence_sub_type_to_delete.delete()

    # Migrate violence sub types to "Non-International armed conflict(NIAC)"
    violence_sub_type_to_rename = ViolenceSubType.objects.get(name='NSAG(s) vs. State actor(s)')
    violence_sub_type_to_rename.name = "Non-International armed conflict(NIAC)"
    violence_sub_type_to_rename.save()
    new_violence_sub_type = violence_sub_type_to_rename

    violence_sub_type_to_delete = ViolenceSubType.objects.filter(
        name__in=[
            'NSAG(s) vs. NSAG(s)',
            'Other (NIAC)',
            'Unclear (NIAC)',
            'Unknown (NIAC)',
        ]
    )
    Event.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    Figure.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    violence_sub_type_to_delete.delete()

    # Migrate violence sub type "other" and "unknown" to "Unclear/Unknown"
    violence_sub_type_to_rename = ViolenceSubType.objects.get(name='Other (Other)')
    violence_sub_type_to_rename.name = "Unclear/Unknown"
    violence_sub_type_to_rename.save()
    new_violence_sub_type = violence_sub_type_to_rename

    violence_sub_type_to_delete = ViolenceSubType.objects.filter(
        name__in=[
            'Unclear (Other)',
            'Unknown (Other)',
            'Unclear (Unknown)',
            'Unknown (Unknown)'
        ]
    )
    Event.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    Figure.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    violence_sub_type_to_delete.delete()

    # Migrate violence sub type from "other(OSV)" to "Other"
    violence_sub_type_to_rename = ViolenceSubType.objects.get(name='Other (OSV)')
    violence_sub_type_to_rename.name = "Other"
    violence_sub_type_to_rename.save()
    new_violence_sub_type = violence_sub_type_to_rename

    violence_sub_type_to_delete = ViolenceSubType.objects.filter(
        name__in=[
            'Unclear (OSV)',
            'Unknown (OSV)',
        ]
    )
    Event.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    Figure.objects.filter(
        violence_sub_type__in=violence_sub_type_to_delete
    ).update(
        violence_sub_type=new_violence_sub_type
    )
    violence_sub_type_to_delete.delete()

    # Rename violence "Other" to "Unclear/Unknown"
    violence_type_to_rename = Violence.objects.get(name='Other')
    violence_type_to_rename.name = 'Unclear/Unknown'
    violence_type_to_rename.save()
    new_violence_type = violence_type_to_rename

    # Change Event violence "Unknown" to "Others"
    violence_type_to_delete = Violence.objects.filter(
        name__in=[
            'Unknown',
        ]
    )
    Event.objects.filter(
        violence__in=violence_type_to_delete
    ).update(
        violence=new_violence_type
    )
    Figure.objects.filter(
        violence__in=violence_type_to_delete
    ).update(
        violence=new_violence_type
    )
    # Delete violence "Unknown"
    violence_type_to_delete.delete()


def migrate_violence_and_sub_types(apps, _):
    Event = apps.get_model('event', 'Event')
    Figure = apps.get_model('entry', 'Figure')
    Violence = apps.get_model('event', 'Violence')
    ViolenceSubType = apps.get_model('event', 'ViolenceSubType')

    if settings.TESTING:
        return
    migrate_data(Event, Figure, Violence, ViolenceSubType)


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0034_alter_eventcode_uuid'),
    ]

    operations = [
        migrations.RunPython(migrate_violence_and_sub_types, reverse_code=migrations.RunPython.noop),
    ]

