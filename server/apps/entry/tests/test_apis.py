import json
from uuid import uuid4

from django.core.files.temp import NamedTemporaryFile

from apps.entry.models import Figure, Entry
from apps.users.roles import MONITORING_EXPERT_EDITOR, MONITORING_EXPERT_REVIEWER, ADMIN, GUEST
from utils.factories import EventFactory, EntryFactory, FigureFactory
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
                createFigure(data: $input) {
                    ok
                    result {
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
            "district": "disss",
            "town": "town",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
            "reported": 10,
            "unit": Figure.UNIT.PERSON.name,
            "term": Figure.TERM.EVACUATED.name,
            "type": Figure.TYPE.IDP_STOCK.name,
            "role": Figure.ROLE.RECOMMENDED.name,
            "startDate": "2020-09-09",
            "includeIdu": False,
            "entry": self.entry.id,
            "ageJson": [
                {
                    "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                     "ageFrom": 1,
                     "ageTo": 3,
                     "value": 3
                },
                {
                    "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                     "ageFrom": 3,
                     "ageTo": 5,
                     "value": 3
                 }
            ],
            "strataJson": [
                {"date": "2020-10-10", "value": 12, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
            ],
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
        self.assertIsNotNone(content['data']['createFigure']['result']['id'], content)


class TestFigureUpdate(HelixGraphQLTestCase):
    def setUp(self):
        self.creator = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.entry = EntryFactory.create(
            created_by=self.creator
        )
        self.figure = FigureFactory.create(
            created_by=self.creator,
            entry=self.entry
        )
        self.mutation = '''
            mutation UpdateFigure($input: FigureUpdateInputType!) {
                updateFigure(data: $input) {
                    ok
                    result {
                        id
                        ageJson{
                            ageFrom
                            uuid
                            ageTo
                            value
                        }
                        strataJson{
                            date
                            value
                            uuid
                        }
                    }
                    errors {
                        field
                        messages
                            arrayErrors {
                                key
                                messages
                                objectErrors {
                                field
                                messages
                                arrayErrors {
                                    key
                                    messages
                                    objectErrors {
                                        field
                                        messages
                                    }
                                }
                            }
                        }
                    }
                }
            }
        '''
        self.input = {
            "id": self.figure.id,
            "ageJson": [
                {
                    "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                    "ageFrom": 1,
                    "ageTo": 3,
                    "value": 13
                },
                {
                    "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                    "ageFrom": 3,
                    "ageTo": 5,
                    "value": 23
                }
            ],
            "strataJson": [
                {"date": "2020-10-10", "value": 12, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
            ]
        }
        self.force_login(self.creator)

    def test_valid_figure_update(self):
        self.assertIsNone(self.figure.age_json)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateFigure']['ok'], content)
        self.assertIsNotNone(content['data']['updateFigure']['result']['id'], content)
        self.figure.refresh_from_db()
        self.assertEqual(len(self.figure.age_json), len(self.input['ageJson']))
        self.assertEqual(len(self.figure.strata_json), len(self.input['strataJson']))

    def test_invalid_age_groups_data(self):
        input1 = {
            "id": self.figure.id,
            "ageJson": [
                {
                    "uuid": str(uuid4()),
                    "ageFrom": 30,
                    "ageTo": 1,
                    "value": 13
                },
            ]
        }
        response = self.query(
            self.mutation,
            input_data=input1
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateFigure']['ok'], content)
        self.assertEqual('ageTo', content['data']['updateFigure']['errors'][0]['arrayErrors'][0]['objectErrors'][0]['field'])

        input2 = {
            "id": self.figure.id,
            "ageJson": [
                {
                    "uuid": str(uuid4()),
                    "ageFrom": 10,
                    "ageTo": 30,
                    "value": 13
                },
                {
                    "uuid": str(uuid4()),
                    "ageFrom": 20,
                    "ageTo": 40,
                    "value": 23
                }
            ]
        }
        response = self.query(
            self.mutation,
            input_data=input2
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateFigure']['ok'], content)
        self.assertEqual('ageJson',
                         content['data']['updateFigure']['errors'][0]['field'],
                         content)
        self.assertIsNotNone(content['data']['updateFigure']['errors'][0]['arrayErrors'][0]['messages'], content)


class TestEntryCreation(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.event = EventFactory.create()
        self.mutation = """
            mutation CreateEntry($input: EntryCreateInputType!) {
                createEntry(data: $input) {
                    ok
                    errors {
                        field
                        messages
                            arrayErrors {
                                key
                                objectErrors {
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
                        }
                    }
                    result {
                        id
                        figures {
                            results {
                                id
                            }
                            totalCount
                        }
                        reviewers {
                            results {
                                id
                            }
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
        self.assertIsNotNone(content['data']['createEntry']['result']['id'])

    def test_valid_nested_figures_create(self):
        figures = [
            {
                "uuid": str(uuid4()),
                "district": "ABC",
                "town": "XYZ",
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "type": Figure.TYPE.IDP_STOCK.name,
                "role": Figure.ROLE.RECOMMENDED.name,
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
        self.assertIsNotNone(content['data']['createEntry']['result']['id'])
        self.assertEqual(content['data']['createEntry']['result']['figures']['totalCount'],
                         len(figures))
        self.assertIsNotNone(content['data']['createEntry']['result']['figures']['results'][0]['id'])

    def test_assert_nested_figures_errors(self):
        uuid = str(uuid4())
        uuid_error = str(uuid4())
        figures = [
            # valid data
            {
                "uuid": uuid,
                "district": "ABC",
                "town": "XYZ",
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "type": Figure.TYPE.IDP_STOCK.name,
                "role": Figure.ROLE.RECOMMENDED.name,
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
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "type": Figure.TYPE.IDP_STOCK.name,
                "role": Figure.ROLE.RECOMMENDED.name,
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
        self.assertFalse(content['data']['createEntry']['ok'], content)
        self.assertIsNotNone(content['data']['createEntry']['errors'], content)
        self.assertEqual('reported',
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['objectErrors'][0]['field'])
        self.assertEqual(uuid_error,
                         content['data']['createEntry']['errors'][0]['arrayErrors'][0]['key'])

    def test_invalid_entry_created_by_reviewer(self):
        reviewer = create_user_with_role(role=MONITORING_EXPERT_REVIEWER)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_add_reviewers_while_create_entry(self):
        r1 = create_user_with_role(role=MONITORING_EXPERT_REVIEWER)
        r2 = create_user_with_role(role=MONITORING_EXPERT_REVIEWER)
        r3 = create_user_with_role(role=MONITORING_EXPERT_REVIEWER)
        self.input.update(dict(reviewers=[str(r1.id), str(r2.id), str(r3.id)]))

        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createEntry']['ok'], content)
        self.assertIsNone(content['data']['createEntry']['errors'], content)
        entry = Entry.objects.get(id=content['data']['createEntry']['result']['id'])
        self.assertEqual(entry.reviewers.count(), len(self.input['reviewers']))
        self.assertEqual(len(content['data']['createEntry']['result']['reviewers']['results']), len(self.input['reviewers']), content)

    def test_invalid_guest_entry_create(self):
        guest = create_user_with_role(role=GUEST)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

    def test_invalid_figures_age_data(self):
        figures = [
            {
                "uuid": str(uuid4()),
                "district": "ABC",
                "town": "XYZ",
                "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
                "reported": 10,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.TERM.EVACUATED.name,
                "type": Figure.TYPE.IDP_STOCK.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt abc",
                "ageJson": [
                    # from is greater than to
                    {"uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9", "ageFrom": 3, "ageTo": 2, "value": 3},
                    {"uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce", "ageFrom": 3, "ageTo": 5, "value": 3}
                ]
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
        self.assertFalse(content['data']['createEntry']['ok'], content)
        self.assertIn('ageTo', json.dumps(content['data']['createEntry']['errors']))


class TestEntryUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(MONITORING_EXPERT_EDITOR)
        self.entry = EntryFactory.create(
            created_by=self.editor
        )
        self.mutation = """
        mutation MyMutation($input: EntryUpdateInputType!) {
          updateEntry(data: $input) {
            ok
            errors {
              field
              messages
              arrayErrors {
                key
                messages
                objectErrors {
                    field
                    messages
                }
              }
            }
            result {
              id
              figures {
                results {
                  id
                  createdAt
                }
              }
              createdAt
              articleTitle
            }
          }
        }
        """
        self.input = {
            "id": self.entry.id,
            "publisher": "updated-publisher",
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

    def test_valid_update_entry_with_figures(self):
        figure = FigureFactory.create(entry=self.entry)
        deleted_figure = FigureFactory.create(entry=self.entry)
        figures = [
            {
            "uuid": "1cd00034-037e-4c5f-b196-fa05b6bed803",
            "district": "disss",
            "town": "town",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
            "reported": 10,
            "unit": Figure.UNIT.PERSON.name,
            "term": Figure.TERM.EVACUATED.name,
            "type": Figure.TYPE.IDP_STOCK.name,
            "role": Figure.ROLE.RECOMMENDED.name,
            "startDate": "2020-09-09",
            "includeIdu": False,
            "ageJson": [
                {
                    "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                     "ageFrom": 1,
                     "ageTo": 3,
                     "value": 3
                },
                {
                    "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                     "ageFrom": 3,
                     "ageTo": 5,
                     "value": 3
                 }
            ],
            "strataJson": [
                {"date": "2020-10-10", "value": 12, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
            ]
            },
            {
            "id": figure.id,
            "uuid": "20a5a258-a83e-47c3-8fff-0c2dab77113a", # str(figure.uuid),
            "district": "disss",
            "town": "town",
            "quantifier": Figure.QUANTIFIER.MORE_THAN.name,
            "reported": 10,
            "unit": Figure.UNIT.PERSON.name,
            "term": Figure.TERM.EVACUATED.name,
            "type": Figure.TYPE.IDP_STOCK.name,
            "role": Figure.ROLE.RECOMMENDED.name,
            "startDate": "2020-09-09",
            "includeIdu": False,
            "ageJson": [
                {
                    "uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9",
                     "ageFrom": 1,
                     "ageTo": 3,
                     "value": 3
                },
                {
                    "uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce",
                     "ageFrom": 3,
                     "ageTo": 5,
                     "value": 3
                 }
            ],
            "strataJson": [
                {"date": "2020-10-10", "value": 12, "uuid": "132acc8b-b7f7-4535-8c80-f6eb35bf9003"},
                {"date": "2020-10-12", "value": 12, "uuid": "bf2b1415-2fc5-42b7-9180-a5b440e5f6d1"}
            ]
            },
        ]
        old_figures_count = self.entry.figures.count()

        self.force_login(self.editor)
        self.input['figures'] = figures
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateEntry']['ok'], content)
        self.entry.refresh_from_db()
        self.assertNotIn(deleted_figure, self.entry.figures.all())
        self.assertEqual(self.entry.figures.count(), old_figures_count)


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
                    result {
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
        self.assertEqual(content['data']['deleteEntry']['result']['url'],
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

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteEntry']['ok'], content)
        self.assertEqual(content['data']['deleteEntry']['result']['url'],
                         self.entry.url)
