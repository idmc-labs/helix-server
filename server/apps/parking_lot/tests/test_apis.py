import json

from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, ParkingLotFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateParkedItem(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_id = str(CountryFactory.create().id)
        self.mutation = '''
        mutation CreateParkedItem($input: ParkedItemCreateInputType!) {
            createParkedItem(data: $input) {
                ok
                errors
                result {
                    id
                    title
                }
            }
        }
        '''

        self.assigned_to = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.input = dict(
            country=self.country_id,
            assignedTo=str(self.assigned_to.id),
            status='TO_BE_REVIEWED',
            title='title',
            url='http://google.com'
        )

    def test_valid_parking_lot_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createParkedItem']['ok'], content)
        self.assertEqual(content['data']['createParkedItem']['result']['title'],
                         self.input['title'])


class TestUpdateParkedItem(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.parking_lot = ParkingLotFactory.create(created_by=self.reviewer)
        self.mutation = '''
        mutation UpdateParkedItem($input: ParkedItemUpdateInputType!) {
            updateParkedItem(data: $input) {
                ok
                errors
                result {
                    id
                    title
                }
            }
        }
        '''
        self.input = {
            "id": self.parking_lot.id,
            "title": "updated title",
        }

    def test_valid_parking_lot_update(self) -> None:
        self.force_login(self.reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateParkedItem']['ok'], content)
        self.assertEqual(content['data']['updateParkedItem']['result']['title'],
                         self.input['title'])
