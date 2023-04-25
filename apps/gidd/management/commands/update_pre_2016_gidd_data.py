import csv
import logging
import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q, Subquery, OuterRef
from apps.country.models import Country
from apps.gidd.models import ConflictLegacy, DisasterLegacy
from apps.event.models import DisasterSubType

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Migrate legacy conflict data"

    def add_arguments(self, parser):
        parser.add_argument('conflict_csv_file')
        parser.add_argument('disaster_csv_file')

    def handle(self, *args, **kwargs):
        country_data = Country.objects.values('id', 'iso3', 'idmc_short_name')
        country_iso3_map = {item['iso3']: item['idmc_short_name'] for item in country_data}
        conflict_csv_file = kwargs['conflict_csv_file']
        disaster_csv_file = kwargs['disaster_csv_file']

        ConflictLegacy.objects.all().delete()
        DisasterLegacy.objects.all().delete()

        hazard_sub_type_map = {
            disaster_sub_type['name']: disaster_sub_type for disaster_sub_type in DisasterSubType.objects.values('id', 'name')
        }

        def get_event_name(event_name, country_name, start_date, hazard_sub_type):
            if event_name:
                return event_name
            date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            formatted_date = date.strftime('%d/%m/%Y')
            return f'{country_name}: {hazard_sub_type["name"]} - {formatted_date}'

        def get_new_hazard_sub_type_id(hazard_sub_type):
            old_to_new_hazard_sub_type_map = {
                'Drought': 'Drought',
                'Extreme temp, Winter Conditions / Cold Wave': 'Cold wave',
                'Wildfire': 'Wildfire',
                'Wildfire - Forest': 'Wildfire',
                'Wildfire - Land fire': 'Wildfire',
                'Wildfire - Firenado': 'Wildfire',
                'Extreme temperature': 'Cold wave',
                'Exterme temp, Severe winter conditions': 'Cold wave',
                'Extreme temp, Extreme Heat / Heat Wave': 'Heat wave',
                'Dry mass movement': 'Dry mass movement',
                'Mass movement, Rock fall': 'Dry mass movement',
                'Mass movement, Sudden subsidence/sinkhole': 'Sinkhole',
                'Mass movement, Landslide': 'Landslide/Wet mass movement',
                'Wet mass movement': 'Landslide/Wet mass movement',
                'Wave action, Seiche': 'Landslide/Wet mass movement',
                'Glacial Lake Outburst Floods (GLOF)': 'Landslide/Wet mass movement',
                'Earthquake': 'Earthquake',
                'Earthquake, Ground Shaking': 'Earthquake',
                'Earthquake, Tsunami': 'Tsunami',
                'Volcanic eruption': 'Volcanic activity',
                'Volcanic activity, Ash fall': 'Volcanic activity',
                'Volcanic activity, Lahar': 'Volcanic activity',
                'Volcanic activity, Pyroclastic flow': 'Volcanic activity',
                'Volcanic activity, Lava flow': 'Volcanic activity',
                'Volcanic activity, Toxic gases': 'Volcanic activity',
                'Flood': 'Flood',
                'Flash flood': 'Flood',
                'Coastal flood': 'Flood',
                'Riverine flood': 'Flood',
                'Ice jam flood': 'Flood',
                'Dam release flood': 'Dam release flood',
                'Landslide, Avalanche': 'Avalanche',
                'Wave action, Rogue wave': 'Rogue Wave',
                'Storm': 'Storm',
                'Storm, Extra-tropical': 'Storm',
                'Storm, Tropical': 'Storm',
                'Storm, Convective': 'Storm',
                'Thunderstorm': 'Storm',
                "Nor'wester": 'Storm',
                'Storm, Storm surge': 'Storm surge',
                'Tornado': 'Tornado',
                'Storm, Tropical, Hurricane': 'Typhoon/Hurricane/Cyclone',
                'Storm, Tropical, Cyclone': 'Typhoon/Hurricane/Cyclone',
                'Storm, Tropical, Typhoon': 'Typhoon/Hurricane/Cyclone',
                'Hailstorm': 'Hailstorm',
                'Winter storm': 'Winter storm/Blizzard',
                'Other': 'Unknown',
                # Extra added mapping by bimal, IDMC should review
                'Landslide': 'Landslide/Wet mass movement',
                'Sudden subsidence': 'Landslide/Wet mass movement',
                'Landslide, avalanche': 'Avalanche',
                'Storm, tropical, cyclone': 'Typhoon/Hurricane/Cyclone',
                'Storm, tropical, typhoon': 'Typhoon/Hurricane/Cyclone',
                'Storm, tropical': 'Typhoon/Hurricane/Cyclone',
                'Wildfire - bush fire': 'Wildfire',
                'Storm, gale': 'Storm',
                'Wildfire - forest': 'Wildfire',
                'Storm, storm surge': 'Storm surge',
                'Storm, tropical, hurricane': 'Typhoon/Hurricane/Cyclone',
                'Storm, wind storm': 'Storm',
                'Glacial lake outburst floods (glof)': 'Landslide/Wet mass movement',
                'Extreme temp, winter conditions / cold wave': 'Cold wave',
                'Storm, dust storm': 'Sand/dust storm',
                'Storm, inter-tropical convergence zone': 'Storm',
                'Melting glacier flood': 'Landslide/Wet mass movement',
                'Earthquake, tsunami': 'Tsunami',
                'Exterme temp, severe winter conditions/dzud': 'Cold wave',
                'Monsoon': 'Storm',
                'Mudslide': 'Landslide/Wet mass movement',
                'Storm, tropical, depression': 'Storm',
                'Extreme temp, severe winter condition': 'Cold wave',
            }
            new_disaster_sub_type = old_to_new_hazard_sub_type_map.get(hazard_sub_type)
            return hazard_sub_type_map.get(new_disaster_sub_type)

        def format_gidd_number(number):
            if number == 0:
                return number
            elif number:
                return number
            else:
                return None

        with open(conflict_csv_file, 'r') as conflict_csv_file:
            reader = csv.DictReader(conflict_csv_file)
            ConflictLegacy.objects.bulk_create(
                [
                    ConflictLegacy(
                        iso3=old_conflict['iso3'],
                        year=old_conflict['year'],
                        country_name=country_iso3_map[old_conflict['iso3']],
                        new_displacement=format_gidd_number(old_conflict['new_displacement']),
                        total_displacement=format_gidd_number(old_conflict['total_displacement']),
                    ) for old_conflict in reader
                ]
            )

        with open(disaster_csv_file, 'r') as disaster_csv_file:
            reader = csv.DictReader(disaster_csv_file)
            DisasterLegacy.objects.bulk_create(
                [
                    DisasterLegacy(
                        iso3=old_disaster['iso3'],
                        year=old_disaster['year'],
                        event_name=get_event_name(
                            old_disaster['event_name'],
                            country_iso3_map[old_disaster['iso3']],
                            old_disaster['start_date'] or None,
                            get_new_hazard_sub_type_id(old_disaster['hazard_sub_type']),
                        ),

                        # FIXME: we will not need to migrate this
                        country_name=country_iso3_map[old_disaster['iso3']],

                        start_date=old_disaster['start_date'] or None,
                        start_date_accuracy=old_disaster['start_date_accuracy'],
                        end_date=old_disaster['end_date'] or None,
                        end_date_accuracy=old_disaster['end_date_accuracy'],

                        # FIXME: we will need to update these from helix or not event migrate this
                        hazard_category_name=old_disaster['hazard_category'],
                        hazard_sub_category_name=old_disaster['hazard_sub_category'],
                        hazard_type_name=old_disaster['hazard_type'],
                        hazard_sub_type_name=old_disaster['hazard_sub_type'],

                        hazard_sub_type_id=get_new_hazard_sub_type_id(old_disaster['hazard_sub_type'])['id'],

                        # FIXME: we should not use format_gidd_number here.
                        new_displacement=format_gidd_number(old_disaster['new_displacement']),
                    ) for old_disaster in reader
                ]
            )

            # Update disaster legacy hazard type, hazard category, hazard sub category
            DisasterLegacy.objects.filter(
                Q(hazard_sub_type__isnull=False)
            ).update(
                hazard_type=Subquery(DisasterLegacy.objects.filter(pk=OuterRef('pk')).values('hazard_sub_type__type')[:1]),
            )
            DisasterLegacy.objects.filter(
                Q(hazard_type__isnull=False)
            ).update(
                hazard_sub_category=Subquery(DisasterLegacy.objects.filter(
                    pk=OuterRef('pk')
                ).values('hazard_type__disaster_sub_category')[:1]),
            )
            DisasterLegacy.objects.filter(
                Q(hazard_sub_category__isnull=False)
            ).update(
                hazard_category=Subquery(DisasterLegacy.objects.filter(
                    pk=OuterRef('pk')
                ).values('hazard_sub_category__category')[:1]),
            )
