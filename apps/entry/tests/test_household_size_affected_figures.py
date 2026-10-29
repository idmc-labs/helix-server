from datetime import date

from apps.entry.models import Figure
from apps.extraction.filters import ReportFigureExtractionFilterSet
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    HouseholdSizeFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestFigureListHouseholdSizeFilter(HelixGraphQLTestCase):
    """figureList(filters: {householdSizeId}) lists the figures an AHHS edit would reach."""

    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.other_country = CountryFactory.create()
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
        figure(country=self.other_country)
        figure(role=Figure.ROLE.TRIANGULATION)
        figure(unit=Figure.UNIT.PERSON, household_size=None)

        self.all_figure_ids = set(Figure.objects.values_list("id", flat=True))

        self.query_ = """
        query AffectedFigures($householdSizeId: ID, $countries: [ID!], $ordering: String) {
          figureList(
            filters: {householdSizeId: $householdSizeId, filterFigureCountries: $countries}
            ordering: $ordering
          ) {
            results {
              id
              householdSize
            }
          }
        }
        """
        self.force_login(create_user_with_role(USER_ROLE.MONITORING_EXPERT.name))

    def _ids(self, **variables):
        variables.setdefault("householdSizeId", str(self.household_size.pk))
        response = self.query(self.query_, variables=variables)
        self.assertResponseNoErrors(response)
        return [int(each["id"]) for each in response.json()["data"]["figureList"]["results"]]

    def test_lists_recommended_household_figures_of_the_rows_country_and_year(self):
        expected = {each.id for each in self.with_value} | {self.with_other_value.id}
        self.assertEqual(set(self._ids()), expected)

    def test_figures_can_be_sorted_by_their_household_size(self):
        self.assertEqual(self._ids(ordering="householdSize")[0], self.with_other_value.id)

    def test_an_unknown_row_lists_nothing(self):
        self.assertEqual(self._ids(householdSizeId="0"), [])

    def test_without_a_row_the_filter_is_not_applied(self):
        self.assertEqual(set(self._ids(householdSizeId=None)), self.all_figure_ids)

    def test_combines_with_other_figure_filters(self):
        self.assertEqual(len(self._ids(countries=[str(self.country.pk)])), len(self.with_value) + 1)
        self.assertEqual(self._ids(countries=[str(self.other_country.pk)]), [])

    def test_applies_to_figure_exports_and_aggregations_too(self):
        # Exports, the crisis figure filter and figureAggregations share the input type
        # but go through ReportFigureExtractionFilterSet, which also applies its own listing rules.
        def ids(data):
            return set(ReportFigureExtractionFilterSet(data=data).qs.values_list("id", flat=True))

        affected = {each.id for each in self.with_value} | {self.with_other_value.id}
        expected = affected & ids({})
        self.assertTrue(expected)
        self.assertEqual(ids({"household_size_id": self.household_size.pk}), expected)
