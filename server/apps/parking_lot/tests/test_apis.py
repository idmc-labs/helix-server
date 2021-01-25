import json

from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, ParkingLotFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateParkingLot(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_id = str(CountryFactory.create().id)
        self.mutation = '''
        mutation CreateParkingLot($input: ParkingLotCreateInputType!) {
            createParkingLot(data: $input) {
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
        self.assertTrue(content['data']['createParkingLot']['ok'], content)
        self.assertEqual(content['data']['createParkingLot']['result']['title'],
                         self.input['title'])


class TestUpdateParkingLot(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.parking_lot = ParkingLotFactory.create(created_by=self.reviewer)
        self.mutation = '''
        mutation UpdateParkingLot($input: ParkingLotUpdateInputType!) {
            updateParkingLot(data: $input) {
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
        self.assertTrue(content['data']['updateParkingLot']['ok'], content)
        self.assertEqual(content['data']['updateParkingLot']['result']['title'],
                         self.input['title'])
