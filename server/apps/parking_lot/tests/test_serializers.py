from django.test import RequestFactory

from apps.users.enums import USER_ROLE
from apps.parking_lot.models import ParkingLot
from apps.parking_lot.serializers import ParkingLotSerializer
from utils.factories import CountryFactory
from utils.tests import HelixTestCase, create_user_with_role


class TestParkingLotSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.sign_off = create_user_with_role(USER_ROLE.ADMIN.name)
        self.data = dict(
            country=CountryFactory.create().id,
            title='lol',
            url='http://google.com',
            owner_sign_off=self.sign_off.id,
            status=ParkingLot.PARKING_LOT_STATUS.TO_BE_REVIEWED.value,
            comments='comment'
        )
        self.request = RequestFactory()

    def test_parking_lot_submitted_by_equals_authenticated_user(self):
        self.request.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        serializer = ParkingLotSerializer(data=self.data,
                                          context=dict(request=self.request))
        self.assertNotIn('submitted_by', self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn('submitted_by', serializer.validated_data)
        self.assertEqual(serializer.validated_data['submitted_by'], self.request.user)
