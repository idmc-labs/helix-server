import json

from apps.users.roles import MONITORING_EXPERT_EDITOR
from utils.factories import CountryFactory, ContactFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCountrySchema(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country1 = CountryFactory.create()
        self.country2, self.country3 = CountryFactory.create_batch(2)
        self.country_q = '''
        query MyQuery {
          country(id: %s) {
            operatingContacts {
              results {
                id
              }
            }
            contacts {
              results {
                id
              }
            }
          }
        }
        '''
        self.contact1 = ContactFactory.create(country=self.country1)
        self.contact1.countries_of_operation.set([self.country2, self.country3])

        self.contact2 = ContactFactory.create(country=self.country2)
        self.contact2.countries_of_operation.set([self.country1, self.country3])

        self.force_login(create_user_with_role(MONITORING_EXPERT_EDITOR))

    def test_fetch_contacts_and_operating_contacts(self):
        response = self.query(self.country_q % self.country1.id)
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertEqual(self.country1.contacts.count(), 1)
        self.assertListEqual([int(each['id']) for each in content['data']['country']['contacts']['results']],
                             [self.contact1.id])
        self.assertListEqual([int(each['id']) for each in content['data']['country']['operatingContacts']['results']],
                             [self.contact2.id])
