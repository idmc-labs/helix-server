from copy import copy
from datetime import timedelta
from django.utils import timezone
from uuid import uuid4

from django.test import RequestFactory

from apps.entry.serializers import (
    EntryCreateSerializer,
    EntryUpdateSerializer,
    FigureSerializer,
)
from apps.users.enums import USER_ROLE
from apps.entry.models import (
    OSMName,
    Figure,
)
from utils.factories import (
    EventFactory,
    EntryFactory,
    OrganizationFactory,
    CountryFactory,
    FigureFactory,
    DisasterCategoryFactory,
    DisasterSubCategoryFactory,
    DisasterTypeFactory,
    DisasterSubTypeFactory,
    ViolenceFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixTestCase, create_user_with_role
from apps.crisis.models import Crisis


class DummyFigureBulkManager():
    @staticmethod
    def add_event(_):
        return


class TestEntrySerializer(HelixTestCase):
    def setUp(self) -> None:
        r1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        r2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.factory = RequestFactory()
        self.country = CountryFactory.create(country_code=123, iso2='ak')
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
        )
        self.event.countries.add(self.country)
        self.publisher = OrganizationFactory.create()
        self.data = {
            "url": "https://yoko-onos-blog.com",
            "article_title": "title 1",
            "publishers": [self.publisher.id],
            "publish_date": "2020-09-09",
            "source_methodology": "method",
            "source_breakdown": "break down",
            "idmc_analysis": "analysis one",
            "methodology": "methoddddd",
            "reviewers": [r1.id, r2.id],
            "calculation_logic": "calculation logic 1",
            "figure_cause": Crisis.CRISIS_TYPE.CONFLICT.value,
        }
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name
        )

    def test_create_entry_requires_document_or_url(self):
        self.data['url'] = None
        self.data['document'] = None
        serializer = EntryCreateSerializer(data=self.data,
                                           context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('url', serializer.errors)
        self.assertIn('document', serializer.errors)

    def test_update_entry_url_and_document_is_redundant(self):
        OLD = 'http://abc.com'
        entry = EntryFactory.create(
            url=OLD
        )
        data = {
            'source_methodology': 'method'
        }
        serializer = EntryCreateSerializer(instance=entry,
                                           data=data,
                                           context={'request': self.request},
                                           partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        data = {
            'url': 'http://abc.com/new-url/',
            'document': None
        }
        serializer = EntryCreateSerializer(instance=entry,
                                           data=data,
                                           context={'request': self.request},
                                           partial=True)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(OLD, entry.url)

    def test_create_entry_populates_created_by(self):
        serializer = EntryCreateSerializer(data=self.data,
                                           context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.created_by, self.user)

    def test_update_entry_populates_last_modified_by(self):
        entry = EntryFactory.create()
        serializer = EntryCreateSerializer(instance=entry,
                                           data=self.data,
                                           context={'request': self.request})
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()
        self.assertEqual(instance.last_modified_by, self.user)
        self.assertIsNotNone(instance.created_at)
        self.assertIsNotNone(instance.modified_at)

    def test_entry_serializer_with_figures_source(self):
        source1 = dict(
            uuid=str(uuid4()),
            rank=101,
            country=str(self.country.name),
            country_code=self.country.iso2,
            osm_id='ted',
            osm_type='okay',
            display_name='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADM0.value,
            identifier=OSMName.IDENTIFIER.ORIGIN.value,
        )
        source2 = copy(source1)
        source2['lat'] = 67.5
        source2['uuid'] = str(uuid4())
        source3 = copy(source1)
        source3['lon'] = 45.9
        source3['uuid'] = str(uuid4())
        flow = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT

        entry_serializer = EntryCreateSerializer(data=self.data, context={'request': self.request})
        self.assertTrue(entry_serializer.is_valid(), True)
        entry = entry_serializer.save()
        figures = [{
            "uuid": "4298b36f-572b-48a4-aa13-a54a3938370f",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 10,
            "category": flow.value,
            "country": str(self.country.id),
            "unit": Figure.UNIT.PERSON.value,
            "term": Figure.FIGURE_TERMS.EVACUATED.value,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-09-09",
            "include_idu": False,
            "geo_locations": [source1, source2, source3],
            "event": self.event.id,
            "figure_cause": Crisis.CRISIS_TYPE.CONFLICT.value,
            "entry": entry.id,
        }]
        figure_serializer = FigureSerializer(
            instance=None,
            data=figures,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
            many=True,
        )
        self.assertTrue(figure_serializer.is_valid(), True)
        figure_serializer.save()
        self.assertEqual(entry.figures.count(), len(figures))

    def test_entry_event_with_incoherent_dates_in_figure(self):
        c1 = CountryFactory.create()
        c2 = CountryFactory.create()
        ref = timezone.now()

        flow = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        stock = Figure.FIGURE_CATEGORY_TYPES.IDPS

        event = EventFactory.create(
            start_date=ref,
            end_date=ref + timedelta(days=1),
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
        )
        event.countries.set([c1])
        event2 = EventFactory.create(
            start_date=ref - timedelta(days=10),
            end_date=ref - timedelta(days=5),
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
        )
        event2.countries.set([c2])

        entry = EntryFactory.create()
        figure = FigureFactory.create(
            entry=entry,
            category=flow,
            country=c1,
            event=event,
            figure_cause=event.event_type,
        )

        source1 = dict(
            uuid=str(uuid4()),
            rank=101,
            country=str(self.country.name),
            country_code=self.country.iso2,
            osm_id='ted',
            osm_type='okay',
            display_name='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADM0.value,
            identifier=OSMName.IDENTIFIER.ORIGIN.value,
        )
        data = dict(
            event=event.id,
            figures=[
                dict(
                    id=figure.id,
                    uuid=figure.uuid,
                    country=c1.id,
                    start_date=event.start_date.strftime('%Y-%m-%d'),
                    end_date=event.end_date.strftime('%Y-%m-%d'),
                    geo_locations=[source1],
                    disaggregation_age=[],
                    figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value,
                )
            ]
        )
        serializer = EntryUpdateSerializer(
            instance=entry,
            data=data,
            context={'request': self.request},
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer = EntryUpdateSerializer(
            instance=entry,
            data=data,
            context={'request': self.request},
            partial=True
        )
        # Because we don't have event in entry this should not raise error
        self.assertTrue(serializer.is_valid())

        # however it will be valid for stock end date to go beyond event date
        figure = FigureFactory.create(
            entry=entry,
            category=stock,
            country=c1,
            event=event,
            figure_cause=event.event_type,
        )

        data = dict(
            event=event.id,
            figures=[
                dict(
                    id=figure.id,
                    uuid=figure.uuid,
                    country=c1.id,
                    start_date=event.start_date.strftime('%Y-%m-%d'),
                    end_date=(event.end_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                    geo_locations=[source1],
                    figure_cause=Crisis.CRISIS_TYPE.CONFLICT.value,
                )
            ]
        )
        serializer = EntryUpdateSerializer(
            instance=entry,
            data=data,
            context={'request': self.request},
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_idmc_analysis_should_be_non_required_field(self):
        self.data['idmc_analysis'] = None
        serializer = EntryCreateSerializer(data=self.data,
                                           context={'request': self.request})
        self.assertTrue(serializer.is_valid())
        self.assertNotIn('idmc_analysis', serializer.errors)
        entry_obj = serializer.save()
        self.assertEqual(entry_obj.idmc_analysis, None)


class TestFigureSerializer(HelixTestCase):
    def setUp(self):
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.factory = RequestFactory()
        country1 = CountryFactory.create(country_code=123, iso2='AD')
        country2 = CountryFactory.create(name='Nepal', iso2='AF')
        self.event = EventFactory.create(
            name="hahaha",
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
        )
        self.event.countries.set([country1, country2])
        self.entry = EntryFactory.create(
            created_by=self.creator,
        )
        self.fig_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        self.country = country1
        source1 = dict(
            uuid=str(uuid4()),
            rank=101,
            country=str(self.country.name),
            country_code=self.country.iso2,
            osm_id='ted',
            osm_type='okay',
            display_name='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADM0.value,
            identifier=OSMName.IDENTIFIER.ORIGIN.value,
        )
        self.data = {
            "uuid": str(uuid4()),
            "entry": self.entry.id,
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 100,
            "unit": Figure.UNIT.PERSON.value,
            "term": Figure.FIGURE_TERMS.EVACUATED.value,
            "category": self.fig_cat.value,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-10-10",
            "include_idu": True,
            "excerpt_idu": "excerpt abc",
            "country": country1.id,
            "geo_locations": [source1],
            "tags": [],
            "event": self.event.id,
            "context_of_violence": [],
            "figure_cause": Crisis.CRISIS_TYPE.DISASTER.value,
            "sources": [str(OrganizationFactory.create().id)],
        }
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

    def test_displacement_occur_only_allowed_for_specific_terms(self):
        term = Figure.FIGURE_TERMS.DISPLACED.value
        self.data['term'] = term
        self.data['displacement_occurred'] = 0
        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.data['displacement_occurred'],
            self.data['displacement_occurred']
        )
        self.data['displacement_occurred'] = None
        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.data['displacement_occurred'])

    def test_invalid_geo_locations_country_codes(self):
        self.data['geo_locations'] = [
            {
                "country": "Nepal",
                "country_code": "23",
                "osm_id": "tets1",
                "osm_type": "HA",
                "identifier": OSMName.IDENTIFIER.ORIGIN.value,
                "display_name": "testname",
                "lon": 12.34,
                "lat": 23.21,
                "name": "testme",
                "accuracy": OSMName.OSM_ACCURACY.ADM0.value,
                "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                "bounding_box": [1.2],
            },
            {
                "country": "Nepal",
                "country_code": "423",
                "osm_id": "tets1",
                "osm_type": "HA",
                "identifier": OSMName.IDENTIFIER.ORIGIN.value,
                "display_name": "testname",
                "lon": 12.34,
                "lat": 23.21,
                "name": "testme",
                "accuracy": OSMName.OSM_ACCURACY.ADM0.value,
                "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                "bounding_box": [1.2],
            },
        ]
        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('geo_locations', serializer.errors)

        # if the figure country iso2 is missing, ignore the validation
        self.country.iso2 = None
        self.country.save()

        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_displacement(self):
        self.data['disaggregation_displacement_urban'] = 10
        self.data['disaggregation_displacement_rural'] = 120
        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_displacement_rural', serializer.errors)

    def test_invalid_disaggregation_age(self):
        self.data['disaggregation_age'] = [
            {
                "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                "category": 1,
                "sex": 0,
                "value": 1000
            },
            {
                "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                "category": 4,
                "sex": 1,
                "value": 23
            }
        ]
        self.data['reported'] = sum([item['value'] for item in self.data['disaggregation_age']]) - 1
        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_age', serializer.errors)

    def test_valid_disaggregation_age_can_be_empty_list(self):
        self.data['disaggregation_age'] = []
        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_should_save_parent_fields_if_sub_field_selected(self):

        disaster_category = DisasterCategoryFactory.create()
        disaster_sub_category = DisasterSubCategoryFactory.create(category=disaster_category)

        disaster_type = DisasterTypeFactory.create(
            disaster_sub_category=disaster_sub_category
        )
        disaster_sub_type = DisasterSubTypeFactory.create(
            type=disaster_type,
        )
        violence = ViolenceFactory.create()
        violence_sub_type = ViolenceSubTypeFactory.create(violence=violence)

        self.data['disaster_sub_type'] = disaster_sub_type.id
        self.data['violence_sub_type'] = violence_sub_type.id
        serializer = FigureSerializer(
            data=self.data,
            context={
                'request': self.request,
                'bulk_manager': DummyFigureBulkManager(),
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        figure = serializer.save()

        # Test sub fields
        self.assertEqual(figure.disaster_sub_category.id, disaster_sub_category.id)
        self.assertEqual(figure.disaster_sub_type.id, disaster_sub_type.id)
        self.assertEqual(figure.violence_sub_type.id, violence_sub_type.id)

        # Test parent fields
        self.assertEqual(figure.disaster_category.id, disaster_category.id)
        self.assertEqual(figure.disaster_type.id, disaster_type.id)
        self.assertEqual(figure.violence.id, violence.id)
