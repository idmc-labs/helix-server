import json

from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateContextualUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = '''mutation MyMutation($input: ContextualUpdateCreateInputType!) {
            createContextualUpdate(data: $input) {
                result {
                    countries {
                        id
                    }
                    url
                    articleTitle
                }
                ok
                errors
            }
        }'''
        self.input = {
            "url": "https://google.com",
            "articleTitle": "ok not ok",
            "publishDate": "2020-10-10T10:10",
            "countries": [str(each.id) for each in countries],
        }

    def test_valid_creation(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createContextualUpdate']['ok'], content)
        self.assertEqual(content['data']['createContextualUpdate']['result']['articleTitle'],
                         self.input['articleTitle'])
        self.assertEqual(len(content['data']['createContextualUpdate']['result']['countries']),
                         len(self.input['countries']))

    def test_invalid_creation_by_guest(self) -> None:
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = json.loads(response.content)
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])
