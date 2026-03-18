import json

from django.utils import timezone

from apps.country.models import HouseholdSize, HouseholdSizeCarryOverTask
from apps.users.enums import USER_ROLE
from utils.factories import ContactFactory, CountryFactory, HouseholdSizeFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCountrySchema(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country1 = CountryFactory.create()
        self.country2, self.country3 = CountryFactory.create_batch(2)
        self.country_q = """
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
        """
        self.contact1 = ContactFactory.create(country=self.country1)
        self.contact1.countries_of_operation.set([self.country2, self.country3])

        self.contact2 = ContactFactory.create(country=self.country2)
        self.contact2.countries_of_operation.set([self.country1, self.country3])

        self.force_login(create_user_with_role(USER_ROLE.MONITORING_EXPERT.name))

    def test_fetch_contacts_and_operating_contacts(self):
        response = self.query(self.country_q % self.country1.id)
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertEqual(self.country1.contacts.count(), 1)
        self.assertEqual(self.country1.operating_contacts.count(), 1)
        self.assertEqual(self.country1.operating_contacts.first(), self.contact2)
        contact_ids = [int(each["id"]) for each in content["data"]["country"]["contacts"]["results"]]
        self.assertEqual(set(contact_ids), {self.contact1.id})
        contact_ids = [int(each["id"]) for each in content["data"]["country"]["operatingContacts"]["results"]]
        self.assertEqual(set(contact_ids), {self.contact2.id})


class TestCarryoverAhhsSchema(HelixGraphQLTestCase):
    AHHS_CARRYOVER_QUERY = """
      mutation {
        carryOverHouseholdSize {
          ok
          errors
        }
      }
    """
    AHHS_LIST_QUERY = """
      query {
        householdSizeList {
          results {
            id
            year
            country {
              iso3
            }
          }
          totalCount
        }
      }
    """
    logout_query = """
        mutation Logout {
            logout {
                ok
            }
        }
    """

    def setUp(self):
        # no destination entries first
        self.destination_year = timezone.now().year
        self.source_year = self.destination_year - 1  # last year

        self.country_npl = CountryFactory.create(iso3="NPL")
        self.country_ind = CountryFactory.create(iso3="IND")
        self.country_usa = CountryFactory.create(iso3="USA")

        self.source_year_ahhs_npl = HouseholdSizeFactory.create(year=self.source_year, country=self.country_npl)
        self.source_year_ahhs_usa = HouseholdSizeFactory.create(year=self.source_year, country=self.country_usa)
        # source_year_ahhs_ind will be created later
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.admin)

        # guest will login later
        self.guest = create_user_with_role(USER_ROLE.GUEST.name)

    def test_carryover_ahhs_should_be_successful(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.AHHS_CARRYOVER_QUERY)
            self.assertResponseNoErrors(response)

        list_response = self.query(self.AHHS_LIST_QUERY)
        ahhs_content = json.loads(list_response.content)

        self.assertResponseNoErrors(list_response)
        self.assertEqual(ahhs_content["data"]["householdSizeList"]["totalCount"], 4)
        self.assertEqual(
            sorted([ahhs["country"]["iso3"] for ahhs in ahhs_content["data"]["householdSizeList"]["results"]]),
            sorted(["NPL", "NPL", "USA", "USA"]),
        )

    def test_carryover_ahhs_should_be_disallowed(self):
        HouseholdSizeFactory.create(year=self.destination_year, country=self.country_ind)
        # now ahhs shouldn't be carried-over
        with self.captureOnCommitCallbacks(execute=True):
            response = self.query(self.AHHS_CARRYOVER_QUERY)
            errors = response.json()["data"]["carryOverHouseholdSize"]["errors"]
            # assertNoErrors doesn't pics the errors dynamically
            self.assertTrue(len(errors) == 1)

        list_response = self.query(self.AHHS_LIST_QUERY)
        ahhs_content = json.loads(list_response.content)

        self.assertEqual(ahhs_content["data"]["householdSizeList"]["totalCount"], 3)
        self.assertEqual(
            sorted([ahhs["country"]["iso3"] for ahhs in ahhs_content["data"]["householdSizeList"]["results"]]),
            sorted(["IND", "NPL", "USA"]),
        )

    def test_no_admin_user_should_be_allowed_to_carryover_ahhs(self):
        self.query(self.logout_query)
        self.force_login(self.guest)

        # carryover is allowed only for a user with permissions
        # 1. super user
        # 2. carry_over_householdsize
        response = self.query(self.AHHS_CARRYOVER_QUERY)
        self.assertResponseErrors(response)
        # FIXME: list is allowed(why?)
        list_response = self.query(self.AHHS_LIST_QUERY)
        self.assertResponseNoErrors(list_response)


class TestHouseholdBulkOperationSchema(HelixGraphQLTestCase):
    AHHS_CARRYOVER_QUERY = """
      mutation {
        carryOverHouseholdSize {
          ok
          errors
          result {
            status
          }
        }
      }
    """
    AHHS_BULK_OPS_LIST_QUERY = """
      query {
        householdSizeBulkOperationList {
            results {
                targetYear
                status
            }
        }
      }
    """

    def setUp(self):
        self.destination_year = timezone.now().year
        self.source_year = self.destination_year - 1  # last year

        self.country_npl = CountryFactory.create(iso3="NPL")
        self.country_ind = CountryFactory.create(iso3="IND")
        self.country_usa = CountryFactory.create(iso3="USA")

        # no destination entries first
        self.source_year_ahhs_npl = HouseholdSizeFactory.create(year=self.source_year, country=self.country_npl)
        self.source_year_ahhs_ind = HouseholdSizeFactory.create(year=self.source_year, country=self.country_ind)
        self.source_year_ahhs_usa = HouseholdSizeFactory.create(year=self.source_year, country=self.country_usa)

        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.admin)

    def test_household_bulk_operation_list(self):
        response = self.query(self.AHHS_BULK_OPS_LIST_QUERY)
        self.assertResponseNoErrors(response)
        # 0, because we haven't created bulk operation just yet
        self.assertEqual(len(response.json()["data"]["householdSizeBulkOperationList"]["results"]), 0)

        # a pending task
        res = self.query(self.AHHS_CARRYOVER_QUERY).json()
        self.assertTrue(res["data"]["carryOverHouseholdSize"]["ok"])
        # assertNoErrors doesn't pics the errors dynamically
        status_value = res["data"]["carryOverHouseholdSize"]["result"]["status"]
        self.assertEqual(HouseholdSizeCarryOverTask.AHHS_CARRYOVER_OPERATION_STATUS.PENDING.label, status_value)

        # cleanup; pending task will block future bulk tasks
        HouseholdSizeCarryOverTask.objects.filter().delete()

        # now execute the background task, should be completed
        with self.captureOnCommitCallbacks(execute=True):
            self.query(self.AHHS_CARRYOVER_QUERY).json()

        response = self.query(self.AHHS_BULK_OPS_LIST_QUERY)
        self.assertResponseNoErrors(response)

        status_value = response.json()["data"]["householdSizeBulkOperationList"]["results"][0]["status"]
        self.assertEqual(HouseholdSizeCarryOverTask.AHHS_CARRYOVER_OPERATION_STATUS.COMPLETED.label, status_value)

        # each for previous year and current year
        self.assertEqual(HouseholdSize.objects.count(), 6)
