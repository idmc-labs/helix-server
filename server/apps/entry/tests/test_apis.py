import json

from django.contrib.auth.models import Permission

from utils.factories import EventFactory, EntryFactory, UserFactory
from utils.tests import HelixGraphQLTestCase


class TestEntryCreation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.event = EventFactory.create()
        self.mutation = """
            mutation CreateEntry($input: EntryCreateInputType!) {
                createEntry(entry: $input) {
                    ok
                    errors {
                        field
                        messages
                    }
                    entry {
                        id
                    }
                }
            }
        """
        self.input = {
            "url": "https://yoko-onos-blog.com",
            "articleTitle": "title 1",
            "source": "source 1",
            "publisher": "publisher 1",
            "publishDate": "2020-09-09",
            "tags": ["2020", "grid2020", "south", "asia"],
            "sourceMethodology": "method",
            "sourceExcerpt": "excerpt one",
            "sourceBreakdown": "break down",
            "idmcAnalysis": "analysis one",
            "methodology": "methoddddd",
            "reviewers": [],
            "event": self.event.id,
        }

    def test_valid_create_entry_without_figures(self):
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEntry']['ok'], content)
        self.assertIsNone(content['data']['createEntry']['errors'], content)
        self.assertIsNotNone(content['data']['createEntry']['entry']['id'])

    def test_valid_nested_figures_create(self):
        self.fail()


class TestEntryUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.monitor_expert = self.create_monitoring_expert()
        self.entry = EntryFactory.create(
            created_by=self.monitor_expert
        )
        self.mutation = """
            mutation UpdateEntry($input: EntryUpdateInputType!) {
                updateEntry(entry: $input) {
                    ok
                    errors {
                        field
                        messages
                    }
                    entry {
                        id
                        url
                    }
                }
            }
        """
        self.input = {
            "id": self.entry.id,
            "url": "https://updated-url.com",
        }

    def test_valid_update_entry(self):
        self.force_login(self.monitor_expert)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn('You do not have permission', response.content)
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntry']['ok'], content)
        self.assertEqual(content['data']['updateEntry']['entry']['url'],
                         self.input['url'])

    def test_invalid_update_by_reviewer(self):
        p = Permission.objects.get(codename='change_entry')
        self.monitor_expert.user_permissions.remove(p)
        self.force_login(self.monitor_expert)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn('You do not have permission', content['errors'])

    def test_invalid_entry_update_by_non_owner(self):
        self.monitor_expert2 = UserFactory.create()
        self.force_login(self.monitor_expert2)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateEntry']['ok'], content)
        self.assertIn('non_field_errors',
                      [each['field'] for each in content['data']['updateEntry']['errors']])
        self.assertIn('You cannot update this entry',
                      json.dumps(content['data']['updateEntry']['errors']))
