import json

from apps.users.enums import USER_ROLE
from apps.review.models import Review
from utils.factories import (
    CountryFactory,
    CrisisFactory,
    EntryFactory,
    EventFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


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
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
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
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
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
        self.input = {
            "id": self.crisis.id,
            "name": "New Name"
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
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
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
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
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
        editor2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
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


class TestCrisisList(HelixGraphQLTestCase):
    def setUp(self):
        self.q = '''
        query crisisList {
          crisisList {
            results {
              reviewCount {
                toBeReviewedCount
                underReviewCount
                reviewCompleteCount
                signedOffCount
              }
            }
          }
        }
        '''
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)

    def test_crisis_review_count_with_dataloader(self):
        crisis = CrisisFactory.create()
        event = EventFactory.create(
            crisis=crisis
        )
        r1 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT_EDITOR.name,
        )
        r2 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT_EDITOR.name,
        )
        entry1 = EntryFactory.create(
            event=event,
        )
        entry1.reviewers.set([r1, r2])

        event2 = EventFactory.create(
            crisis=crisis
        )
        r3 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT_EDITOR.name,
        )
        entry2 = EntryFactory.create(
            event=event2,
        )

        # see that r2 is duplicated across entries
        # so crisis must show 4 not 3
        entry2.reviewers.set([r3, r2])

        response = self.query(
            self.q,
        )
        content = response.json()
        # check the counts
        data = content['data']
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['toBeReviewedCount'],
            4
        )
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['underReviewCount'],
            None
        )
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['signedOffCount'],
            None
        )
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['reviewCompleteCount'],
            None
        )

        # one reviewer starts reviewing an entry
        Review.objects.create(
            entry=entry1,
            created_by=r2,
            field='field',
            value=0,
        )
        response = self.query(
            self.q,
        )
        content = response.json()
        # check the counts
        data = content['data']
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['toBeReviewedCount'],
            3
        )
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['underReviewCount'],
            1
        )
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['signedOffCount'],
            None
        )
        self.assertEqual(
            data['crisisList']['results'][0]['reviewCount']['reviewCompleteCount'],
            None
        )
