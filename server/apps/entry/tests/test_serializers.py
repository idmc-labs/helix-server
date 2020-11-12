from django.test import RequestFactory

from apps.entry.serializers import EntrySerializer
from apps.users.roles import MONITORING_EXPERT_EDITOR
from utils.factories import EventFactory, EntryFactory, OrganizationFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestEntrySerializer(HelixTestCase):
    def setUp(self) -> None:
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
        }
        self.request = self.factory.get('/graphql')
        self.request.user = self.user = create_user_with_role(MONITORING_EXPERT_EDITOR)

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

