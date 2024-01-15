from django.test import TestCase

from utils.factories import (
    EventFactory,
    FigureFactory,
    ViolenceSubTypeFactory,
    ViolenceFactory,
)

from apps.event.models import (
    Event,
    Violence,
    ViolenceSubType,
)
from apps.entry.models import Figure


from apps.event.migrations.change_violence_types_and_sub_types import migrate_data


class ViolenceChangeTestCase(TestCase):
    def test_change_violence_types_and_sub_types(self):
        violence_sub_type_names = [
            'Military Occupation',
            'IAC (other than occupation)',
            'Other (IAC)',
            'Unclear (IAC)',
            'Unknown (IAC)',
            'NSAG(s) vs. State actor(s)',
            'NSAG(s) vs. NSAG(s)',
            'Other (NIAC)',
            'Unclear (NIAC)',
            'Unknown (NIAC)',
            'Civilian-state violence',
            'Crime-related',
            'Communal violence',
            'Other (OSV)',
            'Unclear (OSV)',
            'Unknown (OSV)',
            'Other (Other)',
            'Unclear (Other)',
            'Unknown (Other)',
            'Unclear (Unknown)',
            'Unknown (Unknown)'
        ]

        violence_type_names = [
            'Other',
            'Unknown',
        ]
        for name in violence_type_names:
            ViolenceFactory.create(name=name)

        event = EventFactory.create()
        for name in violence_type_names:
            violence_type = Violence.objects.get(name=name)
            EventFactory.create(violence=violence_type)
            FigureFactory.create(event=event, violence=violence_type)

        for name in violence_sub_type_names:
            ViolenceSubTypeFactory.create(name=name)

        for name in violence_sub_type_names:
            violence_sub_type = ViolenceSubType.objects.get(name=name)
            EventFactory.create(violence_sub_type=violence_sub_type)
            FigureFactory.create(event=event, violence_sub_type=violence_sub_type)

        migrate_data(Event, Figure, Violence, ViolenceSubType)

        assert ViolenceSubType.objects.filter(name__in=['Military Occupation']).count() == 0

        assert Event.objects.filter(violence_sub_type__name='International armed conflict(IAC)').count() == 5
        assert Event.objects.filter(violence_sub_type__name='Unclear/Unknown').count() == 5
        assert Event.objects.filter(violence_sub_type__name='Other').count() == 3
        assert Event.objects.filter(
            violence_sub_type__name__in=[
                'IAC (other than occupation)',
                'Other (IAC)',
                'Unclear (IAC)',
                'Unknown (IAC)',
            ]).count() == 0

        assert Event.objects.filter(violence__name='Unclear/Unknown').count() == 2

        assert Figure.objects.filter(violence_sub_type__name='International armed conflict(IAC)').count() == 5
        assert Figure.objects.filter(violence_sub_type__name='Unclear/Unknown').count() == 5
        assert Figure.objects.filter(violence_sub_type__name='Other').count() == 3
        assert Figure.objects.filter(
            violence_sub_type__name__in=[
                'IAC (other than occupation)',
                'Other (IAC)',
                'Unclear (IAC)',
                'Unknown (IAC)',
            ]).count() == 0

        assert Figure.objects.filter(violence__name='Unclear/Unknown').count() == 2
