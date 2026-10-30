from datetime import date

from apps.entry.models import Figure
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    HouseholdSizeFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestHouseholdSizeAffectedFigureList(HelixGraphQLTestCase):
    """The figures an AHHS edit would reach, listed before the edit is saved."""

    def setUp(self) -> None:
        self.country = CountryFactory.create()
        other_country = CountryFactory.create()
        self.household_size = HouseholdSizeFactory.create(country=self.country, year=2024, size=4.5, is_active=True)

        entry = EntryFactory.create()
        event = EventFactory.create()

        def figure(**kwargs):
            kwargs.setdefault("country", self.country)
            kwargs.setdefault("start_date", date(2024, 6, 1))
            kwargs.setdefault("role", Figure.ROLE.RECOMMENDED)
            kwargs.setdefault("unit", Figure.UNIT.HOUSEHOLD)
            kwargs.setdefault("household_size", 4.5)
            return FigureFactory.create(entry=entry, event=event, **kwargs)

        self.with_value = [figure(), figure(start_date=date(2024, 12, 31))]
        # Matches on country and year, but carries some other household size.
        self.with_other_value = figure(household_size=3.0)
        # None of these can have the row's value copied onto them.
        figure(start_date=date(2023, 12, 31))
        figure(country=other_country)
        figure(role=Figure.ROLE.TRIANGULATION)
        figure(unit=Figure.UNIT.PERSON, household_size=None)

        self.query_ = """
        query AffectedFigures($householdSizeId: ID, $page: Int, $pageSize: Int, $ordering: String) {
          householdSizeAffectedFigureList(
            filters: {householdSizeId: $householdSizeId}
            page: $page
            pageSize: $pageSize
            ordering: $ordering
          ) {
            totalCount
            page
            pageSize
            results {
              id
              householdSize
            }
          }
        }
        """
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)

    def _query(self, **variables):
        variables.setdefault("householdSizeId", str(self.household_size.pk))
        return self.query(self.query_, variables=variables)

    def test_lists_recommended_household_figures_of_the_rows_country_and_year(self):
        self.force_login(self.admin)
        response = self._query()
        self.assertResponseNoErrors(response)
        data = response.json()["data"]["householdSizeAffectedFigureList"]
        expected = {each.id for each in self.with_value} | {self.with_other_value.id}
        self.assertEqual({int(each["id"]) for each in data["results"]}, expected)
        self.assertEqual(data["totalCount"], len(expected))

    def test_without_a_row_nothing_is_listed(self):
        self.force_login(self.admin)
        response = self._query(householdSizeId=None)
        self.assertResponseNoErrors(response)
        data = response.json()["data"]["householdSizeAffectedFigureList"]
        self.assertEqual((data["totalCount"], data["results"]), (0, []))

    def test_an_unknown_row_lists_nothing(self):
        self.force_login(self.admin)
        response = self._query(householdSizeId="0")
        self.assertResponseNoErrors(response)
        self.assertEqual(response.json()["data"]["householdSizeAffectedFigureList"]["totalCount"], 0)

    def test_only_those_who_can_edit_ahhs_see_the_list(self):
        self.force_login(create_user_with_role(USER_ROLE.MONITORING_EXPERT.name))
        response = self._query()
        self.assertResponseErrors(response)
        self.assertIsNone(response.json()["data"]["householdSizeAffectedFigureList"])
