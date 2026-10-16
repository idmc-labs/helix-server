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


class TestUpdateHouseholdSize(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.creator = create_user_with_role(USER_ROLE.ADMIN.name)
        self.household_size = HouseholdSizeFactory.create(
            country=self.country,
            year=2024,
            size=3.0,
            data_source_category="Census",
            source="Old source",
            notes="Old notes",
            is_active=True,
            created_by=self.creator,
            last_modified_by=self.creator,
        )
        self.mutation = """
        mutation UpdateHouseholdSize($input: HouseholdSizeUpdateInputType!) {
            updateHouseholdSize(data: $input) {
                ok
                errors
                result {
                    id
                    year
                    size
                    source
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
        self.input = {
            "id": str(self.household_size.id),
            "size": 5.2,
            "source": "New source",
            "notes": "Corrected value",
        }

    def test_valid_household_size_update_archives_old_value(self) -> None:
        editor = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(editor)
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["updateHouseholdSize"]
        self.assertTrue(data["ok"], content)
        # The edit inserts a new active value
        self.assertNotEqual(data["result"]["id"], str(self.household_size.id))
        self.assertTrue(data["result"]["isActive"])
        self.assertEqual(data["result"]["year"], self.household_size.year)
        self.assertEqual(data["result"]["size"], self.input["size"])
        self.assertEqual(data["result"]["source"], self.input["source"])
        self.assertEqual(data["result"]["notes"], self.input["notes"])
        self.assertEqual(data["result"]["createdBy"]["id"], str(editor.id))
        self.assertEqual(data["result"]["lastModifiedBy"]["id"], str(editor.id))

        # The superseded value is kept as it was
        self.household_size.refresh_from_db()
        self.assertFalse(self.household_size.is_active)
        self.assertEqual(self.household_size.size, 3.0)
        self.assertEqual(self.household_size.source, "Old source")
        self.assertEqual(self.household_size.notes, "Old notes")
        self.assertEqual(self.household_size.last_modified_by, self.creator)
        self.assertEqual(
            HouseholdSize.objects.filter(country=self.country, year=self.household_size.year, is_active=True).count(),
            1,
        )

    def test_partial_update_keeps_other_values(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data={"id": str(self.household_size.id), "size": 4.0})
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["updateHouseholdSize"]
        self.assertTrue(data["ok"], content)
        self.assertEqual(data["result"]["size"], 4.0)
        self.assertEqual(data["result"]["source"], "Old source")
        self.assertEqual(data["result"]["notes"], "Old notes")

    def test_update_without_changes_keeps_active_value(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data={"id": str(self.household_size.id), "size": 3.0})
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["updateHouseholdSize"]
        self.assertTrue(data["ok"], content)
        self.assertEqual(data["result"]["id"], str(self.household_size.id))
        self.assertEqual(HouseholdSize.objects.filter(country=self.country).count(), 1)

    def test_update_archived_household_size_is_rejected(self) -> None:
        archived = HouseholdSizeFactory.create(
            country=self.country,
            year=self.household_size.year,
            size=2.0,
            data_source_category="Census",
            source="Archived source",
            is_active=False,
        )
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data={**self.input, "id": str(archived.id)})
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content["data"]["updateHouseholdSize"]["ok"])
        self.assertIsNotNone(content["data"]["updateHouseholdSize"]["errors"])
        self.household_size.refresh_from_db()
        self.assertTrue(self.household_size.is_active)

    def test_update_does_not_modify_figures(self) -> None:
        figure = FigureFactory.create(country=self.country, event=EventFactory.create(), household_size=3.0)
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data=self.input)
        content = json.loads(response.content)

        self.assertTrue(content["data"]["updateHouseholdSize"]["ok"], content)
        figure.refresh_from_db()
        self.assertEqual(figure.household_size, 3.0)

    def test_update_non_existing_household_size(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data={**self.input, "id": "-1"})
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content["data"]["updateHouseholdSize"]["ok"])
        self.assertIsNotNone(content["data"]["updateHouseholdSize"]["errors"])

    def test_invalid_household_size_update_by_non_admin(self) -> None:
        for role in [USER_ROLE.REGIONAL_COORDINATOR, USER_ROLE.MONITORING_EXPERT, USER_ROLE.GUEST]:
            self.force_login(create_user_with_role(role.name))
            response = self.query(self.mutation, input_data=self.input)
            content = json.loads(response.content)
            self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])

    def test_admin_cannot_delete_household_size(self) -> None:
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.assertTrue(admin.has_perm("country.change_householdsize"))
        self.assertFalse(admin.has_perm("country.delete_householdsize"))
