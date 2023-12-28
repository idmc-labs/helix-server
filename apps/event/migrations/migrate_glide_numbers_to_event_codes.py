from django.db import migrations, transaction
import re


@transaction.atomic
def migrate_glide_numbers_to_event_codes(apps, schema_editor):
    def _check_format(code):
        pattern = re.compile(r'^[A-Z]{2}-[0-9]{4}-[0-9]{6}-[A-Z]{3}$')
        return bool(pattern.match(code))

    Event = apps.get_model('event', 'Event')
    Country = apps.get_model('country', 'Country')
    EventCode = apps.get_model('event', 'EventCode')

    events = Event.objects.filter(
        glide_numbers__isnull=False
    ).exclude(
        glide_numbers=[]
    ).values('id', 'name', 'glide_numbers')

    country_iso3_map = {country.iso3: country for country in Country.objects.all()}

    events_not_migrated = []

    for event in events:
        glide_numbers = event['glide_numbers']
        for glide_no in glide_numbers:
            glide_no = glide_no.replace('\t', '').replace(' ', '')
            is_code_in_format = _check_format(glide_no)
            if is_code_in_format:
                iso3 = glide_no.split('-')[-1]
                country = country_iso3_map.get(str(iso3), None)
                if country:
                    EventCode.objects.get_or_create(
                        country=country,
                        event=Event.objects.get(id=event['id']),
                        event_code=glide_no,
                        event_code_type=1
                    )
            else:
                events_not_migrated.append(
                    {
                        'event_id': event['id'],
                        'event_name': event['name'],
                        'glide_no': glide_no,
                        'countries': [country.iso3 for country in Event.objects.get(id=event['id']).countries.all()],
                        'no_of_countries': len([country.iso3 for country in Event.objects.get(id=event['id']).countries.all()]),
                    }
                )

    print("Count of Invalid Glide numbers: ", len(events_not_migrated))
    print("Not migrated Events: ", events_not_migrated)


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0034_alter_eventcode_uuid'),
    ]

    operations = [
        migrations.RunPython(
            migrate_glide_numbers_to_event_codes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
