import json

from apps.country.models import HouseholdSize
from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, HouseholdSizeFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateHouseholdSize(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.mutation = """
        mutation CreateHouseholdSize($input: HouseholdSizeCreateInputType!) {
            createHouseholdSize(data: $input) {
                ok
                errors
                result {
                    id
                    year
                    size
                    source
                    dataSourceCategory
                    isActive
                    gapFillingMethod
                    createdBy {
                        id
                    }
                }
            }
        }
        """
        self.input = {
            "country": str(self.country.id),
            "year": 2024,
            "size": 4.5,
            "dataSourceCategory": "Census",
            "source": "National statistics office",
            "isActive": True,
            "gapFillingMethod": HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR.name,
        }

    def test_valid_household_size_creation(self) -> None:
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["createHouseholdSize"]
        self.assertTrue(data["ok"], content)
        self.assertEqual(data["result"]["year"], self.input["year"])
        self.assertEqual(data["result"]["size"], self.input["size"])
        self.assertEqual(data["result"]["gapFillingMethod"], self.input["gapFillingMethod"])
        self.assertEqual(data["result"]["createdBy"]["id"], str(admin.id))

    def test_active_household_size_creation_deactivates_previous(self) -> None:
        previous = HouseholdSizeFactory.create(
            country=self.country,
            year=self.input["year"],
            size=3.0,
            data_source_category="Census",
            source="Old source",
            is_active=True,
        )
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["createHouseholdSize"]["ok"], content)
        previous.refresh_from_db()
        self.assertFalse(previous.is_active)
        self.assertEqual(
            HouseholdSize.objects.filter(country=self.country, year=self.input["year"], is_active=True).count(),
            1,
        )

    def test_invalid_household_size_creation_by_non_admin(self) -> None:
        for role in [USER_ROLE.MONITORING_EXPERT, USER_ROLE.GUEST]:
            self.force_login(create_user_with_role(role.name))
            response = self.query(self.mutation, input_data=self.input)
            content = json.loads(response.content)
            self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])
