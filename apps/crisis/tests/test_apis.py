import json

from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    CrisisFactory,
    EventFactory,
    FigureFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from apps.entry.models import Figure


class TestCreateCrisis(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = '''mutation MyMutation($input: CrisisCreateInputType!) {
            createCrisis(data: $input) {
                result {
                    countries {
                        id
                    }
                    name
                }
                ok
                errors
            }
        }'''
        self.input = {
            "name": "disss",
            "crisisType": "DISASTER",
            "countries": [each.id for each in countries],
            "crisisNarrative": "a naarrrative"
        }

    def test_valid_crisis_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createCrisis']['ok'], content)
        self.assertEqual(content['data']['createCrisis']['result']['name'], self.input['name'])
        self.assertEqual(len(content['data']['createCrisis']['result']['countries']),
                         len(self.input['countries']))

    def test_invalid_crisis_creation_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestCrisisUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.crisis = CrisisFactory.create(
            created_by=self.editor
        )
        self.mutation = """
            mutation UpdateCrisis($input: CrisisUpdateInputType!) {
              updateCrisis(data: $input) {
                ok
                errors
                result {
                  name
                }
              }
            }
        """
        country = CountryFactory.create()
        self.input = {
            "id": self.crisis.id,
            "name": "New Name",
            "countries": [country.id],
        }

    def test_valid_update_crisis(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateCrisis']['ok'], content)
        self.assertEqual(content['data']['updateCrisis']['result']['name'],
                         self.input['name'])

    def test_valid_update_crisis_by_different_user(self):
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateCrisis']['ok'], content)
        self.assertEqual(content['data']['updateCrisis']['result']['name'],
                         self.input['name'])

    def test_invalid_update_crisis_by_guest(self):
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestCrisisDelete(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.crisis = CrisisFactory.create(
            created_by=self.editor
        )
        self.mutation = """
            mutation DeleteCrisis($id: ID!) {
              deleteCrisis(id: $id) {
                ok
                errors
                result {
                  name
                }
              }
            }
        """
        self.variables = {
            "id": self.crisis.id,
        }

    def test_valid_delete_crisis(self):
        self.force_login(self.editor)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteCrisis']['ok'], content)
        self.assertIsNotNone(content['data']['deleteCrisis']['result']['name'])

    def test_valid_delete_crisis_by_different_monitoring_expert(self):
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(editor2)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['deleteCrisis']['ok'], content)
        self.assertIsNotNone(content['data']['deleteCrisis']['result']['name'])

    def test_invalid_delete_crisis_by_guest(self):
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestEventRewviewCount(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.crisis = CrisisFactory.create()
        self.event = EventFactory.create(crisis=self.crisis)
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.f1, self.f2, self.f3 = FigureFactory.create_batch(3, event=self.event, role=Figure.ROLE.RECOMMENDED)
        self.event_query = '''
        query MyQuery {
          crisisList {
            results {
              reviewCount {
                progress
                reviewApprovedCount
                reviewInProgressCount
                reviewNotStartedCount
                reviewReRequestCount
                totalCount
              }
            }
          }
        }
        '''

    def test_progress(self) -> None:
        self.force_login(self.admin)
        response = self.query(
            self.event_query,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        crisis_data = content['data']['crisisList']['results'][0]
        self.assertEqual(crisis_data['reviewCount']['progress'], 0)
        self.assertEqual(crisis_data['reviewCount']['reviewApprovedCount'], 0)
        self.assertEqual(crisis_data['reviewCount']['reviewInProgressCount'], 0)
        self.assertEqual(crisis_data['reviewCount']['reviewNotStartedCount'], 3)
        self.assertEqual(crisis_data['reviewCount']['reviewReRequestCount'], 0)

        self.f1.review_status = Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS
        self.f1.save()
        response = self.query(
            self.event_query,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        crisis_data = content['data']['crisisList']['results'][0]
        self.assertEqual(crisis_data['reviewCount']['progress'], 0)
        self.assertEqual(crisis_data['reviewCount']['reviewApprovedCount'], 0)
        self.assertEqual(crisis_data['reviewCount']['reviewInProgressCount'], 1)
        self.assertEqual(crisis_data['reviewCount']['reviewNotStartedCount'], 2)
        self.assertEqual(crisis_data['reviewCount']['reviewReRequestCount'], 0)

        for figure in [self.f1, self.f2, self.f3]:
            figure.review_status = Figure.FIGURE_REVIEW_STATUS.APPROVED
            figure.save()

        response = self.query(
            self.event_query,
        )
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        crisis_data = content['data']['crisisList']['results'][0]
        self.assertEqual(crisis_data['reviewCount']['progress'], 1.0)
        self.assertEqual(crisis_data['reviewCount']['reviewApprovedCount'], 3)
        self.assertEqual(crisis_data['reviewCount']['reviewInProgressCount'], 0)
        self.assertEqual(crisis_data['reviewCount']['reviewNotStartedCount'], 0)
        self.assertEqual(crisis_data['reviewCount']['reviewReRequestCount'], 0)
