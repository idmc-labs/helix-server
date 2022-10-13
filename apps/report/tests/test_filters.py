from django.test import RequestFactory
from utils.tests import HelixTestCase


class TestReportFilter(HelixTestCase):

    def setUp(self) -> None:
        self.request = RequestFactory().post('/graphql')
