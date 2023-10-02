from django.core.management.base import BaseCommand
from django.db.models import Q, OuterRef, Subquery

from apps.event.models import Event
from apps.entry.models import Figure


class Command(BaseCommand):
    help = 'Fix hazard sub types from csv'

    def handle(self, *args, **options):
        '''
        with open('new_hazard_sub_types.csv', 'r') as file:
            csvreader = csv.DictReader(file)
            for row in csvreader:
                figure_id = row['Id']
                hazard_sub_type_name = row['New Hazard Sub Type']

                figure = Figure.objects.get(id=figure_id)
                disaster_sub_type = DisasterSubType.objects.get(name=hazard_sub_type_name)

                figure.event.disaster_sub_type = disaster_sub_type
                figure.save()

                figure.disaster_sub_type = disaster_sub_type
                figure.save()
        '''

        # Regenerate event and figure disaster type
        update = Event.objects.filter(
            Q(disaster_sub_type__isnull=False)
        ).update(
            disaster_type=Subquery(
                Event.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type')[:1]
            ),
        )
        print(f'Updated disaster type for {update} events')
        update = Figure.objects.filter(
            Q(disaster_sub_type__isnull=False)
        ).update(
            disaster_type=Subquery(
                Figure.objects.filter(pk=OuterRef('pk')).values('disaster_sub_type__type')[:1]
            ),
        )
        print(f'Updated disaster type for {update} figures')

        # Regenerate event and figure disaster sub category
        update = Event.objects.filter(
            Q(disaster_type__isnull=False)
        ).update(
            disaster_sub_category=Subquery(
                Event.objects.filter(pk=OuterRef('pk')).values('disaster_type__disaster_sub_category')[:1]
            ),
        )
        print(f'Updated disaster sub-category for {update} events')
        update = Figure.objects.filter(
            Q(disaster_type__isnull=False)
        ).update(
            disaster_sub_category=Subquery(
                Figure.objects.filter(pk=OuterRef('pk')).values('disaster_type__disaster_sub_category')[:1]
            ),
        )
        print(f'Updated disaster sub-category for {update} figures')

        # Regenerate event and figure disaster category
        update = Event.objects.filter(
            Q(disaster_sub_category__isnull=False)
        ).update(
            disaster_category=Subquery(
                Event.objects.filter(pk=OuterRef('pk')).values('disaster_sub_category__category')[:1]
            ),
        )
        print(f'Updated disaster category for {update} events')
        update = Figure.objects.filter(
            Q(disaster_sub_category__isnull=False)
        ).update(
            disaster_category=Subquery(
                Figure.objects.filter(pk=OuterRef('pk')).values('disaster_sub_category__category')[:1]
            ),
        )
        print(f'Updated disaster category for {update} figures')

        # Regenerate figure and event violence from violence sub type
        update = Figure.objects.filter(
            violence_sub_type__isnull=False
        ).update(
            violence=Subquery(
                Figure.objects.filter(pk=OuterRef('pk')).values('violence_sub_type__violence')[:1]
            )
        )
        print(f'Updated violence type for {update} events')
        update = Event.objects.filter(
            violence_sub_type__isnull=False
        ).update(
            violence=Subquery(
                Event.objects.filter(pk=OuterRef('pk')).values('violence_sub_type__violence')[:1]
            )
        )
        print(f'Updated violence type for {update} figures')
