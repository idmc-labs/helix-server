from apps.users.filters import UserFilter
from utils.tests import HelixTestCase
from utils.factories import UserFactory


class TestUserFilter(HelixTestCase):
    def setUp(self) -> None:
        pass

    def test_filter_by_full_name(self):
        u1 = UserFactory.create(first_name='abc', last_name='def')
        UserFactory.create(first_name='bcd', last_name='efa')
        u3 = UserFactory.create(first_name='abc', last_name='dzy')

        data = dict(full_name='abc d')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u1, u3])

        data = dict(full_name='def')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u1])

        data = dict(full_name='zy')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u3])

    def test_filter_users_is_active(self):
        u1 = UserFactory.create(first_name='abc', last_name='def', is_active=False)
        u2 = UserFactory.create(first_name='bcd', last_name='efa', is_active=True)

        data = dict()
        data['is_active'] = 'true'
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u2])
        data['is_active'] = 'false'
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u1])
