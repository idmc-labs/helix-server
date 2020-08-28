import json
from uuid import uuid4

from apps.entry.models import Figure
from apps.users.roles import MONITORING_EXPERT_EDITOR, MONITORING_EXPERT_REVIEWER, ADMIN, GUEST
from utils.factories import EventFactory, EntryFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestFigureCreation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.creator = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.entry = EntryFactory.create(
            created_by=self.creator
        )
        self.mutation = '''
            mutation CreateFigure($input: FigureCreateInputType!) {
                createFigure(figure: $input) {
                    ok
                    figure {
                       id
                    }
                    errors {
                        field
                        messages
                    }
                }
            }
        '''
        self.input = {
            "entry": self.entry.id,
            "district": "abc",
            "town": "xyz",
            "quantifier": Figure.QUANTIFIER.more_than.label,
            "reported": 15,
            "unit": Figure.UNIT.person.label,
            "term": Figure.TERM.evacuated.label,
            "type": Figure.TYPE.idp_stock.label,
            "role": Figure.ROLE.recommended.label,
            "startDate": "2020-10-10",
            "includeIdu": False,
        }
        self.force_login(self.creator)

    def test_invalid_create_figure_into_non_existing_entry(self):
        # set entry to non existing value
        self.input['entry'] = '99911'
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createFigure']['ok'], content)
        self.assertIn('non_field_errors',
                      [each['field'] for each in content['data']['createFigure']['errors']])
        self.assertIn('Entry does not exist',
                      json.dumps(content['data']['createFigure']['errors']))

    def test_invalid_figure_create_by_non_creator_entry(self):
        creator2 = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.force_login(creator2)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createFigure']['ok'], content)
        self.assertIn('non_field_errors',
                      [each['field'] for each in content['data']['createFigure']['errors']])
        self.assertIn('You cannot create a figure into',
                      json.dumps(content['data']['createFigure']['errors']))

    def test_valid_figure_create_by_creator_of_entry(self):
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createFigure']['ok'], content)
        self.assertIsNotNone(content['data']['createFigure']['figure']['id'], content)


class TestEntryCreation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.event = EventFactory.create()
        self.mutation = """
            mutation CreateEntry($input: EntryCreateInputType!) {
                createEntry(entry: $input) {
                    ok
                    errors {
                        field
                        messages
                        arrayErrors {
                            key
                            objectErrors {
                                field
                                messages
                            }
                        }
                    }
                    entry {
                        id
                        figures {
                            results {
                                id
                            }
                            totalCount
                        }
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
        self.force_login(self.editor)

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
        figures = [
            {
                "uuid": str(uuid4()),
                "district": "ABC",
                "town": "XYZ",
                "quantifier": Figure.QUANTIFIER.more_than.label,
                "reported": 10,
                "unit": Figure.UNIT.person.label,
                "term": Figure.TERM.evacuated.label,
                "type": Figure.TYPE.idp_stock.label,
                "role": Figure.ROLE.recommended.label,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            }
        ]
        self.input.update({
            'figures': figures
        })
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEntry']['ok'], content)
        self.assertIsNone(content['data']['createEntry']['errors'], content)
        self.assertIsNotNone(content['data']['createEntry']['entry']['id'])
        self.assertEqual(content['data']['createEntry']['entry']['figures']['totalCount'],
                         len(figures))
        self.assertIsNotNone(content['data']['createEntry']['entry']['figures']['results'][0]['id'])

    def test_assert_nested_figures_errors(self):
        uuid = str(uuid4())
        uuid_error = str(uuid4())
        figures = [
            # valid data
            {
                "uuid": uuid,
                "district": "ABC",
                "town": "XYZ",
                "quantifier": Figure.QUANTIFIER.more_than.label,
                "reported": 10,
                "unit": Figure.UNIT.person.label,
                "term": Figure.TERM.evacuated.label,
                "type": Figure.TYPE.idp_stock.label,
                "role": Figure.ROLE.recommended.label,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            },
            # invalid now
            {
                "uuid": uuid_error,
                "reported": -1,  # this cannot be negative
                "district": "ABC",
                "town": "XYZ",
                "quantifier": Figure.QUANTIFIER.more_than.label,
                "unit": Figure.UNIT.person.label,
                "term": Figure.TERM.evacuated.label,
                "type": Figure.TYPE.idp_stock.label,
                "role": Figure.ROLE.recommended.label,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
            }
        ]
        self.input.update({
            'figures': figures
        })
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        print(json.dumps(content['data']['createEntry']['errors']))
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['createEntry']['ok'], content)
        self.assertIsNotNone(content['data']['createEntry']['errors'], content)
        self.assertEqual('reported',
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['objectErrors'][0]['field'])
        self.assertEqual(uuid_error,
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['key'])

    def test_invalid_reviewer_entry_create(self):
        reviewer = create_user_with_role(role=MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_guest_entry_create(self):
        guest = create_user_with_role(role=GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestEntryUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.entry = EntryFactory.create(
            created_by=self.editor
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
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntry']['ok'], content)
        self.assertEqual(content['data']['updateEntry']['entry']['url'],
                         self.input['url'])

    def test_invalid_update_by_reviewer(self):
        reviewer = create_user_with_role(role=MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_entry_update_by_non_owner(self):
        self.editor2 = create_user_with_role(role=MONITORING_EXPERT_EDITOR)
        self.force_login(self.editor2)
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

    def test_valid_entry_update_by_admins(self):
        admin = create_user_with_role(ADMIN)
        self.force_login(admin)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntry']['ok'], content)
        self.assertEqual(content['data']['updateEntry']['entry']['url'],
                         self.input['url'])


class TestEntryDelete(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.entry = EntryFactory.create(
            created_by=self.editor
        )
        self.mutation = """
            mutation DeleteEntry($id: ID!) {
                deleteEntry(id: $id) {
                    ok
                    errors {
                        field
                        messages
                    }
                    entry {
                        id
                        source
                        url
                        createdAt
                    }
                }
            }
        """
        self.variables = {
            "id": self.entry.id,
        }

    def test_valid_delete_entry(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteEntry']['ok'], content)
        self.assertEqual(content['data']['deleteEntry']['entry']['url'],
                         self.entry.url)

    def test_invalid_delete_by_reviewer(self):
        reviewer = create_user_with_role(role=MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_entry_delete_by_non_owner(self):
        editor2 = create_user_with_role(role=MONITORING_EXPERT_EDITOR)
        self.force_login(editor2)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['deleteEntry']['ok'], content)
        self.assertIn('non_field_errors',
                      [each['field'] for each in content['data']['deleteEntry']['errors']])
        self.assertIn('You cannot delete this entry',
                      json.dumps(content['data']['deleteEntry']['errors']))

    def test_valid_entry_delete_by_admins(self):
        admin = create_user_with_role(ADMIN)
        self.force_login(admin)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        print(content)
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteEntry']['ok'], content)
        self.assertEqual(content['data']['deleteEntry']['entry']['url'],
                         self.entry.url)
