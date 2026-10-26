import json

from apps.country.models import HouseholdSize
from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, EventFactory, FigureFactory, HouseholdSizeFactory
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
        self.assertTrue(data["result"]["isActive"])

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
        self.assertEqual(previous.size, 3.0)
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


class TestCorrectHouseholdSize(HelixGraphQLTestCase):
    """
    Creating a value for a country-year that already has an active value corrects it.
    """

    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.creator = create_user_with_role(USER_ROLE.ADMIN.name)
        self.household_size = HouseholdSizeFactory.create(
            country=self.country,
            year=2024,
            size=3.0,
            data_source_category="Census",
            source="Old source",
            source_link="https://example.com/old",
            notes="Old notes",
            is_active=True,
            created_by=self.creator,
            last_modified_by=self.creator,
        )
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
                    sourceLink
                    notes
                    isActive
                    createdBy {
                        id
                    }
                    lastModifiedBy {
                        id
                    }
                }
            }
        }
        """
        self.base_input = {
            "country": str(self.country.id),
            "year": self.household_size.year,
            "size": self.household_size.size,
            "dataSourceCategory": self.household_size.data_source_category,
            "source": self.household_size.source,
        }
        self.input = {
            **self.base_input,
            "size": 5.2,
            "source": "New source",
            "notes": "Corrected value",
        }

    def test_valid_household_size_correction_archives_old_value(self) -> None:
        editor = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(editor)
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["createHouseholdSize"]
        self.assertTrue(data["ok"], content)
        # The correction inserts a new active value
        self.assertNotEqual(data["result"]["id"], str(self.household_size.id))
        self.assertTrue(data["result"]["isActive"])
        self.assertEqual(data["result"]["year"], self.household_size.year)
        self.assertEqual(data["result"]["size"], self.input["size"])
        self.assertEqual(data["result"]["source"], self.input["source"])
        # The new value keeps the notes of the value it replaces
        self.assertEqual(data["result"]["notes"], "Old notes")
        self.assertEqual(data["result"]["createdBy"]["id"], str(editor.id))
        self.assertEqual(data["result"]["lastModifiedBy"]["id"], str(editor.id))

        # The superseded value keeps its data, and its notes record the reason for the correction
        self.household_size.refresh_from_db()
        self.assertFalse(self.household_size.is_active)
        self.assertEqual(self.household_size.size, 3.0)
        self.assertEqual(self.household_size.source, "Old source")
        self.assertEqual(self.household_size.notes, self.input["notes"])
        self.assertEqual(self.household_size.last_modified_by, self.creator)
        self.assertEqual(
            HouseholdSize.objects.filter(country=self.country, year=self.household_size.year, is_active=True).count(),
            1,
        )

    def test_correction_keeps_values_not_sent(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data={**self.base_input, "size": 4.0})
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["createHouseholdSize"]
        self.assertTrue(data["ok"], content)
        self.assertEqual(data["result"]["size"], 4.0)
        self.assertEqual(data["result"]["sourceLink"], "https://example.com/old")
        self.assertEqual(data["result"]["notes"], "Old notes")
        # Without a reason, the archived value keeps its notes
        self.household_size.refresh_from_db()
        self.assertFalse(self.household_size.is_active)
        self.assertEqual(self.household_size.notes, "Old notes")

    def test_correction_with_only_notes_keeps_active_value(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data={**self.base_input, "notes": "No change"})
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["createHouseholdSize"]
        self.assertTrue(data["ok"], content)
        self.assertEqual(data["result"]["id"], str(self.household_size.id))
        self.household_size.refresh_from_db()
        self.assertTrue(self.household_size.is_active)
        self.assertEqual(self.household_size.notes, "Old notes")
        self.assertEqual(HouseholdSize.objects.filter(country=self.country).count(), 1)

    def test_correction_without_changes_keeps_active_value(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data=self.base_input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["createHouseholdSize"]
        self.assertTrue(data["ok"], content)
        self.assertEqual(data["result"]["id"], str(self.household_size.id))
        self.assertEqual(HouseholdSize.objects.filter(country=self.country).count(), 1)

    def test_correction_does_not_modify_figures(self) -> None:
        figure = FigureFactory.create(country=self.country, event=EventFactory.create(), household_size=3.0)
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertTrue(content["data"]["createHouseholdSize"]["ok"], content)
        figure.refresh_from_db()
        self.assertEqual(figure.household_size, 3.0)

    def test_invalid_household_size_correction_by_non_admin(self) -> None:
        for role in [USER_ROLE.REGIONAL_COORDINATOR, USER_ROLE.MONITORING_EXPERT, USER_ROLE.GUEST]:
            self.force_login(create_user_with_role(role.name))
            response = self.query(self.mutation, input_data=self.input)
            content = json.loads(response.content)
            self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])

    def test_admin_cannot_delete_household_size(self) -> None:
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.assertFalse(admin.has_perm("country.delete_householdsize"))
