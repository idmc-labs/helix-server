from copy import copy
from uuid import uuid4

from django.test import RequestFactory

from apps.entry.serializers import (
    EntryCreateSerializer,
    EntryUpdateSerializer,
    NestedFigureCreateSerializer as FigureSerializer,
)
from apps.users.enums import USER_ROLE
from apps.entry.models import (
    EntryReviewer,
    OSMName,
    Figure,
    FigureTerm,
)
from utils.factories import (
    EventFactory,
    EntryFactory,
    OrganizationFactory,
    CountryFactory,
    FigureCategoryFactory
)
from utils.tests import HelixTestCase, create_user_with_role


class TestEntrySerializer(HelixTestCase):
    def setUp(self) -> None:
        r1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        r2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.factory = RequestFactory()
        self.country = CountryFactory.create(country_code=123, iso2='ak')
        self.event = EventFactory.create()
        self.event.countries.add(self.country)
        self.publisher = OrganizationFactory.create()
        self.data = {
            "url": "https://yoko-onos-blog.com",
            "article_title": "title 1",
            "sources": [self.publisher.id],
            "publishers": [self.publisher.id],
            "publish_date": "2020-09-09",
            "source_methodology": "method",
            "source_excerpt": "excerpt one",
            "source_breakdown": "break down",
            "idmc_analysis": "analysis one",
            "methodology": "methoddddd",
            "event": self.event.id,
            "reviewers": [r1.id, r2.id]
        }
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT_EDITOR.name)

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

    def test_entry_creation_create_entry_reviewers(self):
        reviewer1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        reviewer2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.data['reviewers'] = [reviewer1.id, reviewer2.id]
        serializer = EntryCreateSerializer(data=self.data,
                                           context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        entry = serializer.instance
        self.assertEqual(entry.reviewers.count(), len([reviewer1, reviewer2]))
        self.assertEqual(
            sorted(list(entry.reviewers.through.objects.values_list('reviewer', flat=1))),
            sorted([reviewer1.id, reviewer2.id])
        )

    def test_entry_update_entry_reviewers(self):
        x = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        y = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        z = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        entry = EntryFactory.create()
        entry.reviewers.set([x, y, z])

        reviewer1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        reviewer2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        reviewer3 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        entry = EntryFactory.create()
        entry.reviewers.set([reviewer1, reviewer2, reviewer3])
        self.assertEqual(
            sorted(list(
                entry.reviewers.filter(
                    reviewing__status=EntryReviewer.REVIEW_STATUS.TO_BE_REVIEWED
                ).values_list('id', flat=1))
            ),
            sorted([each.id for each in [reviewer1, reviewer2, reviewer3]])
        )
        entry.reviewing.all().update(
            status=EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
        )

        old_count = EntryReviewer.objects.count()
        serializer = EntryCreateSerializer(instance=entry, data={
            'reviewers': [reviewer1.id, reviewer2.id]
        }, context={'request': self.request}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(entry.reviewers.count(), 2)
        self.assertEqual(entry.reviewing.count(), 2)
        self.assertEqual(set(entry.reviewing.values_list('status', flat=1)),
                         {EntryReviewer.REVIEW_STATUS.UNDER_REVIEW})

        self.assertEqual(old_count - 1, EntryReviewer.objects.count())

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
            accuracy=OSMName.OSM_ACCURACY.COUNTRY.value,
            identifier=OSMName.IDENTIFIER.ORIGIN.value,
        )
        source2 = copy(source1)
        source2['lat'] = 67.5
        source2['uuid'] = str(uuid4())
        source3 = copy(source1)
        source3['lon'] = 45.9
        source3['uuid'] = str(uuid4())
        figures = [{
            "uuid": "4298b36f-572b-48a4-aa13-a54a3938370f",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 10,
            "country": str(self.country.id),
            "unit": Figure.UNIT.PERSON.value,
            "term": FigureTerm.objects.first().id,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-09-09",
            "include_idu": False,
            "geo_locations": [source1, source2, source3],
        }]
        self.data['figures'] = figures

        serializer = EntryCreateSerializer(instance=None,
                                           data=self.data,
                                           context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        entry = serializer.save()
        self.assertEqual(entry.figures.count(), len(figures))
        figure = entry.figures.first()
        self.assertEqual(figure.geo_locations.count(),
                         len(figures[0]['geo_locations']))

        # now trying to update
        new_source = copy(source1)
        new_source.update({
            'lat': 33.8,
            'lon': 33.8,
            'identifier': OSMName.IDENTIFIER.ORIGIN.value,
        })
        new_source['uuid'] = str(uuid4())

        new_source2 = copy(source1)
        new_source2.update({
            'lat': 33.8,
            'lon': 33.8,
            'identifier': OSMName.IDENTIFIER.ORIGIN.value,
        })
        new_source2['uuid'] = str(uuid4())
        existing = figure.geo_locations.first()
        old_source = copy(source2)
        old_source.update({
            'id': existing.id,
        })
        figures = [{
            "uuid": "4298b36f-572b-48a4-aa13-a54a3938370f",
            "id": figure.id,
            "geo_locations": [new_source, old_source],
        }, {
            "uuid": "f1b42e79-da44-4032-8cb6-0dd4b7b97b57",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 10,
            "unit": Figure.UNIT.PERSON.value,
            "term": FigureTerm.objects.first().id,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-09-09",
            "include_idu": False,
            "country": str(self.country.id),
            "geo_locations": [new_source2],
        }]
        self.data['figures'] = figures
        serializer = EntryUpdateSerializer(instance=entry,
                                           data=self.data,
                                           context={'request': self.request},
                                           partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        entry = serializer.save()
        entry.refresh_from_db()
        self.assertEqual(entry.figures.count(), len(figures))

        expected_sources_count = {len(each['geo_locations']) for each in figures}
        existing_count = {each.geo_locations.count() for each in entry.figures.all()}
        self.assertEqual(expected_sources_count, existing_count,
                         f'expected: {expected_sources_count}, obtained: {existing_count}')

        # now checking if source on a different figure can be updated using this serializer
        loc1 = OSMName.objects.create(**source1)
        figure = entry.figures.first()
        different_source = {
            'id': loc1.id,
        }

        figures = [dict(
            uuid=str(uuid4()),
            id=figure.id,
            geo_locations=[different_source]  # I do not belong to above entry figures
        )]
        self.data['figures'] = figures
        serializer = EntryUpdateSerializer(instance=entry,
                                           data=self.data,
                                           context={'request': self.request},
                                           partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('figures', serializer.errors)
        self.assertIn('geo_locations', serializer.errors['figures'][0].keys())

    # TODO: test entry serializer validation for figure household size


class TestFigureSerializer(HelixTestCase):
    def setUp(self):
        self.creator = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.factory = RequestFactory()
        country1 = CountryFactory.create(country_code=123, iso2='lo')
        country2 = CountryFactory.create(name='Nepal', iso2='bo')
        self.event = EventFactory.create(name="hahaha")
        self.event.countries.set([country1, country2])
        self.entry = EntryFactory.create(
            created_by=self.creator,
            event=self.event
        )
        self.fig_cat = FigureCategoryFactory.create()
        self.data = {
            "uuid": str(uuid4()),
            "entry": self.entry.id,
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 100,
            "unit": Figure.UNIT.PERSON.value,
            "term": FigureTerm.objects.first().id,
            "category": self.fig_cat.id,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-10-10",
            "include_idu": True,
            "excerpt_idu": "excerpt abc",
            "country": country1.id,
        }
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)

    def test_displacement_occur_only_allowed_for_specific_terms(self):
        term = FigureTerm.objects.first()
        term.displacement_occur = True
        term.save()
        self.data['term'] = term.id
        self.data['displacement_occurred'] = 0

        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.data['displacement_occurred'],
            self.data['displacement_occurred']
        )

        term.displacement_occur = False
        term.save()
        term.refresh_from_db()

        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.data['displacement_occurred'])

    def test_invalid_geo_locations(self):
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
                "accuracy": OSMName.OSM_ACCURACY.COUNTRY.value,
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
                "accuracy": OSMName.OSM_ACCURACY.COUNTRY.value,
                "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                "bounding_box": [1.2],
            },
        ]
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('geo_locations', serializer.errors)

    def test_invalid_displacement(self):
        self.data['disaggregation_displacement_urban'] = 10
        self.data['disaggregation_displacement_rural'] = 120
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_displacement_rural', serializer.errors)

    def test_invalid_gender(self):
        self.data['disaggregation_sex_male'] = 10
        self.data['disaggregation_sex_female'] = 120
        self.data['reported'] = self.data['disaggregation_sex_male'] + self.data['disaggregation_sex_female'] - 1
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_sex_male', serializer.errors)
        self.data['reported'] = self.data['disaggregation_sex_male'] + self.data['disaggregation_sex_female']
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_conflict(self):
        self.data['disaggregation_conflict'] = 12
        self.data['disaggregation_conflict_communal'] = 23
        self.data['disaggregation_conflict_criminal'] = 45
        self.data['disaggregation_conflict_political'] = 50
        self.data['disaggregation_conflict_other'] = 50
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_conflict', serializer.errors)

    def test_invalid_disaggregation_age_json(self):
        self.data['disaggregation_age_json'] = [
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
        self.data['reported'] = sum([item['value'] for item in self.data['disaggregation_age_json']]) - 1
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_age_json', serializer.errors)

    def test_invalid_disaggregation_strata_json(self):
        self.data['disaggregation_strata_json'] = [
            {"date": "2020-10-10", "value": 120, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
            {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
        ]
        self.data['reported'] = sum([item['value'] for item in self.data['disaggregation_strata_json']]) - 1
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_strata_json', serializer.errors)
