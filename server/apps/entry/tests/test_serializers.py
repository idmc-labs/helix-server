from copy import copy
from uuid import uuid4

from django.test import RequestFactory

from apps.entry.serializers import EntrySerializer
from apps.users.enums import USER_ROLE
from apps.entry.models import EntryReviewer, OSMName, Figure
from utils.factories import EventFactory, EntryFactory, OrganizationFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestEntrySerializer(HelixTestCase):
    def setUp(self) -> None:
        r1 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        r2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.factory = RequestFactory()
        self.event = EventFactory.create()
        self.publisher = OrganizationFactory.create()
        self.data = {
            "url": "https://yoko-onos-blog.com",
            "article_title": "title 1",
            "source": self.publisher.id,
            "publisher": self.publisher.id,
            "publish_date": "2020-09-09",
            "tags": ["2020", "grid2020", "south", "asia"],
            "source_methodology": "method",
            "source_excerpt": "excerpt one",
            "source_breakdown": "break down",
            "idmc_analysis": "analysis one",
            "methodology": "methoddddd",
            "event": self.event.id,
            "reviewers": [r1.id, r2.id]
        }
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)

    def test_create_entry_requires_document_or_url(self):
        self.data['url'] = None
        self.data['document'] = None
        serializer = EntrySerializer(data=self.data,
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
        serializer = EntrySerializer(instance=entry,
                                     data=data,
                                     context={'request': self.request},
                                     partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        data = {
            'url': 'http://abc.com/new-url/',
            'document': None
        }
        serializer = EntrySerializer(instance=entry,
                                     data=data,
                                     context={'request': self.request},
                                     partial=True)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(OLD, entry.url)

    def test_create_entry_populates_created_by(self):
        serializer = EntrySerializer(data=self.data,
                                     context={'request': self.request})
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()
        self.assertEqual(instance.created_by, self.user)

    def test_update_entry_populates_last_modified_by(self):
        entry = EntryFactory.create()
        serializer = EntrySerializer(instance=entry,
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
        serializer = EntrySerializer(data=self.data,
                                     context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        entry = serializer.instance
        self.assertEqual(entry.reviewers.count(), len([reviewer1, reviewer2]))
        self.assertEqual(sorted(list(entry.reviewers.through.objects.values_list('reviewer', flat=1))),
                         sorted([reviewer1.id, reviewer2.id]))

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
        entry.reviewers.through.objects.all().update(
            status=EntryReviewer.REVIEW_STATUS.UNDER_REVIEW
        )

        old_count = EntryReviewer.objects.count()
        serializer = EntrySerializer(instance=entry, data={
            'reviewers': [reviewer1.id, reviewer2.id]
        }, context={'request': self.request}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertTrue(entry.reviewers.count(), 2)
        self.assertTrue(entry.reviewers.through.objects.count(), 2)
        self.assertEqual(set(entry.reviewers.through.objects.values_list('status', flat=1)),
                         {EntryReviewer.REVIEW_STATUS.UNDER_REVIEW})

        self.assertEqual(old_count-1, EntryReviewer.objects.count())

    def test_entry_serializer_with_figures_source(self):
        source1 = dict(
            rank=101,
            country='abc',
            country_code='xyz',
            osm_id='ted',
            osm_type='okay',
            display_name='okay',
            lat=68.88,
            lon=46.66,
            name='name',
            accuracy=OSMName.OSM_ACCURACY.ADMIN.value,
            reported_name='reported',
            identifier=OSMName.IDENTIFIER.SOURCE.value,
            )
        source2 = copy(source1)
        source2['lat'] = 67.5
        source3 = copy(source1)
        source3['lon'] = 45.9
        figures = [{
            "uuid": "4298b36f-572b-48a4-aa13-a54a3938370f",
            "district": "disctrict",
            "town": "town",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
            "reported": 10,
            "unit": Figure.UNIT.PERSON.value,
            "term": Figure.TERM.EVACUATED.value,
            "type": Figure.TYPE.IDP_STOCK.value,
            "role": Figure.ROLE.RECOMMENDED.value,
            "start_date": "2020-09-09",
            "include_idu": False,
            "geo_locations": [source1, source2, source3],
            }]
        self.data['figures'] = figures

        serializer = EntrySerializer(instance=None,
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
            'identifier': OSMName.IDENTIFIER.SOURCE.value,
            'reported_name': 'new source',
        })
        existing = figure.geo_locations.first()
        old_source = {
            'id': existing.id,
            'reported_name': 'updated old source'
        }
        figures = [{
                "uuid": "4298b36f-572b-48a4-aa13-a54a3938370f",
                "id": figure.id,
                "geo_locations": [new_source, old_source],
                "district": "new name",
            }, {
                "uuid": "f1b42e79-da44-4032-8cb6-0dd4b7b97b57",
                "district": "district",
                "town": "town",
                "quantifier": Figure.QUANTIFIER.MORE_THAN.value,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.value,
                "term": Figure.TERM.EVACUATED.value,
                "type": Figure.TYPE.IDP_STOCK.value,
                "role": Figure.ROLE.RECOMMENDED.value,
                "start_date": "2020-09-09",
                "include_idu": False,
                "geo_locations": [new_source],
            }]
        self.data['figures'] = figures
        serializer = EntrySerializer(instance=entry,
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
            'reported_name': 'different source'
        }
        figures = [dict(
            uuid=str(uuid4()),
            id=figure.id,
            geo_locations=[different_source]  # I do not belong to above entry figures
        )]
        self.data['figures'] = figures
        serializer = EntrySerializer(instance=entry,
                                     data=self.data,
                                     context={'request': self.request},
                                     partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('figures', serializer.errors)
        self.assertIn('geo_locations', serializer.errors['figures'][0].keys())
