import re

from django.db import transaction, models
from django.core.management.base import BaseCommand

from apps.event.models import Event, EventCode
from apps.country.models import Country


def is_glid_no_valid(code):
    pattern = re.compile(r'^[A-Z]{2}-[0-9]{4}-[0-9]{6}-[A-Z]{3}$')
    return bool(pattern.match(code))


@transaction.atomic
def migrate_glide_numbers_to_event_codes():
    # TODO: Add unit test cases for this

    event_qs = (
        Event.objects.exclude(
            # TODO: Validated if this filter works
            models.Q(glide_numbers__isnull=True) |
            models.Q(glide_numbers=[]) |
            models.Q(event_codes__isnull=False)
        )
    )

    country_iso3_map = {
        country.iso3: country
        for country in Country.objects.all()
    }

    events_not_migrated = []

    for event in event_qs.values('id', 'name', 'glide_numbers'):
        glide_numbers = event['glide_numbers']
        for glide_no in glide_numbers:
            glide_no = glide_no.replace('\t', '').replace(' ', '')
            is_code_in_format = is_glid_no_valid(glide_no)
            if is_code_in_format:
                iso3 = glide_no.split('-')[-1]
                country = country_iso3_map.get(str(iso3), None)
                if country:
                    EventCode.objects.get_or_create(
                        country=country,
                        event_id=event['id'],
                        event_code=glide_no,
                        event_code_type=1
                    )
            else:
                event_countris_iso3_list = list(
                    Event.countries.through
                    .objects
                    .filter(event=event['id'])
                    .values_list('country__iso3', flat=True)
                )
                events_not_migrated.append(
                    {
                        'event_id': event['id'],
                        'event_name': event['name'],
                        'glide_no': glide_no,
                        'countries': event_countris_iso3_list,
                        'no_of_countries': len(event_countris_iso3_list),
                    }
                )

    print("Count of Invalid Glide numbers: ", len(events_not_migrated))
    print("Not migrated Events: ", events_not_migrated)


class Command(BaseCommand):
    help = 'Migrate existing glide-numbers to new event codes'

    def handle(self, *args, **_):
        migrate_glide_numbers_to_event_codes()
