from utils.tests import HelixTestCase
from utils.factories import UserFactory
from apps.users.filters import UserFilter


class TestUserFilter(HelixTestCase):
    def setUp(self) -> None:
        pass

    def test_filter_by_full_name(self):
        u1 = UserFactory.create(first_name='abc', last_name='def')
        u2 = UserFactory.create(first_name='bcd', last_name='efa')
        u3 = UserFactory.create(first_name='abc', last_name='dzy')

        data = dict(full_name='abcd')
        filtered = UserFilter(data).qs
        print(filtered.count())
        self.assertEqual([each for each in filtered], [u1, u3])

        data = dict(full_name='def')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u2, u1])

        data = dict(full_name='zy')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u3])
