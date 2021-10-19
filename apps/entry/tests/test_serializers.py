from copy import copy
from datetime import timedelta
from django.utils import timezone
from uuid import uuid4
from unittest.mock import patch

from django.test import RequestFactory

from apps.contrib.models import SourcePreview, Attachment
from apps.entry.serializers import (
    EntryCreateSerializer,
    EntryUpdateSerializer,
    NestedFigureCreateSerializer as FigureSerializer,
    CloneEntrySerializer,
)
from apps.users.enums import USER_ROLE
from apps.entry.models import (
    EntryReviewer,
    OSMName,
    Figure,
    FigureCategory,
    FigureTerm,
)
from utils.factories import (
    EventFactory,
    EntryFactory,
    OrganizationFactory,
    CountryFactory,
    FigureFactory,
    FigureCategoryFactory
)
from utils.tests import HelixTestCase, create_user_with_role


class TestEntrySerializer(HelixTestCase):
    def setUp(self) -> None:
        r1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        r2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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
            "source_breakdown": "break down",
            "idmc_analysis": "analysis one",
            "methodology": "methoddddd",
            "event": self.event.id,
            "reviewers": [r1.id, r2.id],
            "calculation_logic": "calculation logic 1"
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

    def test_entry_creation_create_entry_reviewers(self):
        reviewer1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        reviewer2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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
        x = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        y = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        z = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        entry = EntryFactory.create()
        entry.reviewers.set([x, y, z])

        reviewer1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        reviewer2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        reviewer3 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
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
            accuracy=OSMName.OSM_ACCURACY.ADM0.value,
            identifier=OSMName.IDENTIFIER.ORIGIN.value,
        )
        source2 = copy(source1)
        source2['lat'] = 67.5
        source2['uuid'] = str(uuid4())
        source3 = copy(source1)
        source3['lon'] = 45.9
        source3['uuid'] = str(uuid4())

        FigureCategory._invalidate_category_ids_cache()
        flow = FigureCategory.flow_new_displacement_id()
        figures = [{
            "uuid": "4298b36f-572b-48a4-aa13-a54a3938370f",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 10,
            "category": flow.id,
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

    def test_entry_event_with_incoherent_dates_in_figure(self):
        c1 = CountryFactory.create()
        c2 = CountryFactory.create()
        ref = timezone.now()

        FigureCategory._invalidate_category_ids_cache()
        flow = FigureCategory.flow_new_displacement_id()
        stock = FigureCategory.stock_idp_id()

        event = EventFactory.create(start_date=ref, end_date=ref + timedelta(days=1))
        event.countries.set([c1])
        event2 = EventFactory.create(start_date=ref - timedelta(days=10), end_date=ref - timedelta(days=5))
        event2.countries.set([c2])

        entry = EntryFactory.create(event=event)
        figure = FigureFactory.create(entry=entry, category=flow, country=c1)

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
                    disaggregation_age=[]
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

        data['event'] = event2.id
        serializer = EntryUpdateSerializer(
            instance=entry,
            data=data,
            context={'request': self.request},
            partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('figures', serializer.errors)
        self.assertIn('country', serializer.errors['figures'][0])

        # however it will be valid for stock end date to go beyond event date
        figure = FigureFactory.create(entry=entry, category=stock, country=c1)

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

    @patch('apps.entry.serializers.Entry')
    def test_limit_entry_figures_count(self, Entry):
        Entry.FIGURES_PER_ENTRY = 1

        # one figure is allowed
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
        flow = FigureCategory.flow_new_displacement_id()
        figures = [{
            "uuid": str(uuid4()),
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 10,
            "category": flow.id,
            "country": str(self.country.id),
            "unit": Figure.UNIT.PERSON.value,
            "term": FigureTerm.objects.first().id,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-09-09",
            "include_idu": False,
            "geo_locations": [source1],
        }]
        self.data['figures'] = figures

        serializer = EntryCreateSerializer(instance=None,
                                           data=self.data,
                                           context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # more figures are not allowed
        source2 = copy(source1)
        source2['uuid'] = str(uuid4())

        figures = figures.append({
            "uuid": str(uuid4()),
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 10,
            "category": flow.id,
            "country": str(self.country.id),
            "unit": Figure.UNIT.PERSON.value,
            "term": FigureTerm.objects.first().id,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-09-09",
            "include_idu": False,
            "geo_locations": [source1],
        })
        self.data['figures'] = figures

        serializer = EntryCreateSerializer(instance=None,
                                           data=self.data,
                                           context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('figures', serializer.errors)

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
        country1 = CountryFactory.create(country_code=123, iso2='lo')
        country2 = CountryFactory.create(name='Nepal', iso2='bo')
        self.event = EventFactory.create(name="hahaha")
        self.event.countries.set([country1, country2])
        self.entry = EntryFactory.create(
            created_by=self.creator,
            event=self.event
        )
        self.fig_cat = FigureCategoryFactory.create()
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
            "term": FigureTerm.objects.first().id,
            "category": self.fig_cat.id,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-10-10",
            "include_idu": True,
            "excerpt_idu": "excerpt abc",
            "country": country1.id,
            "geo_locations": [source1],
            "tags": []
        }
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

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
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('geo_locations', serializer.errors)

        # if the figure country iso2 is missing, ignore the validation
        self.country.iso2 = None
        self.country.save()

        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_displacement(self):
        self.data['disaggregation_displacement_urban'] = 10
        self.data['disaggregation_displacement_rural'] = 120
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
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
        serializer = FigureSerializer(data=self.data,
                                      context={'request': self.request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('disaggregation_age', serializer.errors)

    def test_valid_disaggregation_age_can_be_empty_list(self):
        self.data['disaggregation_age'] = []
        serializer = FigureSerializer(
            data=self.data,
            context={'request': self.request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestCloneEntry(HelixTestCase):
    def setUp(self):
        self.article_title = 'title1'
        self.preview = SourcePreview.objects.create()
        self.attachment = Attachment.objects.create()
        self.entry = EntryFactory.create(
            article_title=self.article_title,
            preview=self.preview,
            document=self.attachment,
        )
        self.events = EventFactory.create_batch(3)
        self.request = RequestFactory().get('/graphql')

    def test_same_entry_attributes_copied_across_given_events(self):
        data = dict(
            entry=self.entry.id,
            events=[each.id for each in self.events]
        )
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        context = dict(request=self.request)
        serializer = CloneEntrySerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        entries = serializer.save()
        self.assertEqual(1, len(set([each.article_title for each in entries])))
        self.assertEqual(
            f"Clone: {self.article_title}",
            list(set([
                each.article_title for each in entries
            ]))[0]
        )

    def test_cloning_entry_references_to_same_attachment(self):
        data = dict(
            entry=self.entry.id,
            events=[each.id for each in self.events]
        )
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        context = dict(request=self.request)
        serializer = CloneEntrySerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        entries = serializer.save()
        self.assertEqual(1, len(set([each.preview_id for each in entries])), [each.preview_id for each in entries])
        self.assertIsNotNone(entries[0].preview_id)
        self.assertEqual(1, len(set([each.document_id for each in entries])), [each.document_id for each in entries])
        self.assertIsNotNone(entries[0].document_id)

    def test_cloning_does_not_clone_figures(self):
        FigureFactory.create(
            entry=self.entry
        )
        data = dict(
            entry=self.entry.id,
            events=[each.id for each in self.events]
        )
        self.request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        context = dict(request=self.request)
        serializer = CloneEntrySerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        entries = serializer.save()
        self.assertNotEqual(self.entry.figures.count(), 0)
        new_entry = entries[0]
        self.assertEqual(new_entry.figures.count(), 0)
