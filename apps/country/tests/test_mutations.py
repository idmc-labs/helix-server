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
            "referenceDate": "2024-06-30",
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
        self.assertEqual(data["result"]["gapFillingMethod"], HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR.name)
        self.assertEqual(data["result"]["createdBy"]["id"], str(admin.id))
        self.assertTrue(data["result"]["isActive"])

    def test_gap_filling_method_is_derived_from_reference_date(self) -> None:
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        for reference_date, expected in [
            ("2020-01-01", HouseholdSize.GAP_FILLING_METHOD.FORWARD_FILLING.name),
            ("2026-01-01", HouseholdSize.GAP_FILLING_METHOD.BACKWARD_FILLING.name),
            (None, None),
        ]:
            response = self.query(self.mutation, input_data={**self.input, "referenceDate": reference_date})
            content = json.loads(response.content)

            self.assertResponseNoErrors(response)
            data = content["data"]["createHouseholdSize"]
            self.assertTrue(data["ok"], content)
            self.assertEqual(data["result"]["gapFillingMethod"], expected)

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
                    referenceDate
                    gapFillingMethod
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

    def test_correction_recalculates_gap_filling_method(self) -> None:
        HouseholdSize.objects.filter(pk=self.household_size.pk).update(
            reference_date="2024-01-01",
            gap_filling_method=HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR,
        )
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(self.mutation, input_data={**self.base_input, "referenceDate": "2021-01-01"})
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        data = content["data"]["createHouseholdSize"]
        self.assertTrue(data["ok"], content)
        self.assertEqual(data["result"]["referenceDate"], "2021-01-01")
        self.assertEqual(data["result"]["gapFillingMethod"], HouseholdSize.GAP_FILLING_METHOD.FORWARD_FILLING.name)
        self.household_size.refresh_from_db()
        self.assertFalse(self.household_size.is_active)
        self.assertEqual(self.household_size.gap_filling_method, HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR)

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


class TestCarryOverHouseholdSize(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_a = CountryFactory.create()
        self.country_b = CountryFactory.create()
        self.mutation = """
        mutation CarryOverHouseholdSize($targetYear: Int!) {
            carryOverHouseholdSize(targetYear: $targetYear) {
                ok
                errors
                result {
                    id
                    year
                    size
                    country {
                        id
                    }
                    isActive
                    gapFillingMethod
                    createdBy {
                        id
                    }
                }
            }
        }
        """

    def carry_over(self, target_year: int) -> dict:
        response = self.query(self.mutation, variables={"targetYear": target_year})
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]["carryOverHouseholdSize"]

    def test_carries_latest_active_value_of_every_country(self) -> None:
        HouseholdSizeFactory.create(country=self.country_a, year=2024, size=3.0, is_active=False)
        HouseholdSizeFactory.create(country=self.country_a, year=2024, size=4.0, is_active=True, notes="Census")
        # NOTE: A country without a value in the previous year carries its latest earlier one
        HouseholdSizeFactory.create(country=self.country_b, year=2021, size=5.0, is_active=True)
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)

        data = self.carry_over(2025)

        self.assertTrue(data["ok"], data)
        sizes = {int(item["country"]["id"]): item["size"] for item in data["result"]}
        self.assertEqual(sizes, {self.country_a.id: 4.0, self.country_b.id: 5.0})
        for item in data["result"]:
            self.assertEqual(item["year"], 2025)
            self.assertTrue(item["isActive"])
            self.assertEqual(item["createdBy"]["id"], str(admin.id))
        carried = HouseholdSize.objects.get(country=self.country_a, year=2025)
        self.assertEqual(carried.notes, "Census")

    def test_gap_filling_method_matches_import_command(self) -> None:
        for country, reference_date in [
            (self.country_a, "2024-06-30"),
            (self.country_b, "2026-01-01"),
        ]:
            HouseholdSizeFactory.create(country=country, year=2024, reference_date=reference_date, is_active=True)
        no_reference_country = CountryFactory.create()
        HouseholdSizeFactory.create(country=no_reference_country, year=2024, reference_date=None, is_active=True)
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

        data = self.carry_over(2025)

        self.assertTrue(data["ok"], data)
        methods = {int(item["country"]["id"]): item["gapFillingMethod"] for item in data["result"]}
        self.assertEqual(
            methods,
            {
                self.country_a.id: HouseholdSize.GAP_FILLING_METHOD.FORWARD_FILLING.name,
                self.country_b.id: HouseholdSize.GAP_FILLING_METHOD.BACKWARD_FILLING.name,
                no_reference_country.id: None,
            },
        )
        for value in HouseholdSize.objects.filter(year=2025, reference_date__isnull=False):
            self.assertEqual(
                value.gap_filling_method,
                HouseholdSize.calculate_gap_filling_method(2025, value.reference_date.year),
            )

    def test_refuses_when_target_year_has_any_value(self) -> None:
        HouseholdSizeFactory.create(country=self.country_a, year=2024, is_active=True)
        HouseholdSizeFactory.create(country=self.country_b, year=2024, is_active=True)
        # NOTE: Even an archived value in the target year refuses the whole operation
        HouseholdSizeFactory.create(country=self.country_b, year=2025, is_active=False)
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

        data = self.carry_over(2025)

        self.assertFalse(data["ok"], data)
        self.assertEqual(data["errors"][0]["field"], "nonFieldErrors")
        self.assertEqual(HouseholdSize.objects.filter(year=2025).count(), 1)

    def test_refuses_when_nothing_to_carry_over(self) -> None:
        HouseholdSizeFactory.create(country=self.country_a, year=2026, is_active=True)
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))

        data = self.carry_over(2025)

        self.assertFalse(data["ok"], data)
        self.assertFalse(HouseholdSize.objects.filter(year=2025).exists())

    def test_carry_over_by_non_admin(self) -> None:
        HouseholdSizeFactory.create(country=self.country_a, year=2024, is_active=True)
        for role in [USER_ROLE.MONITORING_EXPERT, USER_ROLE.REGIONAL_COORDINATOR, USER_ROLE.GUEST]:
            self.force_login(create_user_with_role(role.name))
            response = self.query(self.mutation, variables={"targetYear": 2025})
            content = json.loads(response.content)
            self.assertIn(PERMISSION_DENIED_MESSAGE, content["errors"][0]["message"])
        self.assertFalse(HouseholdSize.objects.filter(year=2025).exists())
