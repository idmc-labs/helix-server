from typing import Any, Dict, List

from apps.crisis.models import Crisis
from apps.entry.models import (
    Figure,
)
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestFigureAggegationVisualization(HelixGraphQLTestCase):
    aggregation_query = """
        query MyQuery (
            $filterFigureCountries: [ID!]
            $filterFigureEndBefore: Date
        ) {
        figureAggregations(
            filters: {
                filterFigureCountries: $filterFigureCountries
                filterFigureEndBefore: $filterFigureEndBefore
            }
        )
            {
                idpsConflictFigures {
                    date
                    value
                }
                idpsDisasterFigures {
                    date
                    value
                }
                ndsDisasterFigures {
                    date
                    value
                }
                ndsConflictFigures {
                    date
                    value
                }
            }
        }
    """

    def setUp(self) -> None:
        self.country_nep = CountryFactory.create(name="Nepal", iso3="NPL")
        self.country_ind = CountryFactory.create(name="India", iso3="IND")

        self.entry_one = EntryFactory.create()
        self.entry_two = EntryFactory.create()

        self.event_crisis = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        self.event_disaster = EventFactory.create(event_type=Crisis.CRISIS_TYPE.DISASTER)

        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry_one,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=101,
            unit=Figure.UNIT.PERSON,
            end_date="2021-09-12",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date="2021-09-12",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date="2021-10-10",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=5,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date="2022-08-17",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=7,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date="2022-12-10",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=11,
            entry=self.entry_one,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date="2023-12-12",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=13,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date="2023-01-01",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=17,
            entry=self.entry_one,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date="2023-01-01",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry_one,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=101,
            unit=Figure.UNIT.PERSON,
            start_date="2021-09-01",
            end_date="2021-09-12",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2020-09-01",
            end_date="2021-09-12",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2021-10-01",
            end_date="2021-10-10",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=5,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2022-08-01",
            end_date="2022-08-17",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=7,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2022-12-01",
            end_date="2022-12-10",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=11,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2021-12-12",
            end_date="2022-12-12",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=13,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2021-01-01",
            end_date="2022-01-01",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=17,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2022-01-01",
            end_date="2023-01-01",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry_one,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=101,
            unit=Figure.UNIT.PERSON,
            start_date="2021-09-12",
            end_date="2021-09-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2021-09-12",
            end_date="2022-09-30",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2021-10-10",
            end_date="2023-09-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=5,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2022-08-17",
            end_date="2022-08-30",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=7,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2022-12-10",
            end_date="2022-12-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=11,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2023-12-12",
            end_date="2023-12-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=13,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2023-01-01",
            end_date="2023-12-30",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=17,
            entry=self.entry_two,
            event=self.event_crisis,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2023-01-01",
            end_date="2023-12-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry_one,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=101,
            unit=Figure.UNIT.PERSON,
            start_date="2021-09-12",
            end_date="2021-09-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2021-09-12",
            end_date="2022-09-30",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2021-10-10",
            end_date="2023-09-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=5,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2022-08-17",
            end_date="2022-08-30",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=7,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2022-12-10",
            end_date="2022-12-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=11,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2023-12-12",
            end_date="2023-12-30",
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=13,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2023-01-01",
            end_date="2023-12-30",
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=17,
            entry=self.entry_two,
            event=self.event_disaster,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date="2023-01-01",
            end_date="2023-12-30",
        )

        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)

        self.force_login(self.admin)

    @staticmethod
    def _sorted_list_by_field(data: List[Dict[str, Any]], field: str = "date") -> List[Dict[str, Any]]:
        assert field is not None

        return sorted(data, key=lambda x: x[field])

    def test_idps_conflict_figures(self):
        expected_data = [
            {"date": "2021-09-12", "value": 4},
            {"date": "2022-08-17", "value": 5},
            {"date": "2023-01-01", "value": 13},
            {"date": "2023-12-12", "value": 11},
        ]
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_nep.id}).json()

        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["idpsConflictFigures"]),
            self._sorted_list_by_field(expected_data),
        )

        expected_data = [
            {"date": "2021-10-10", "value": 3},
            {"date": "2022-12-10", "value": 7},
            {"date": "2023-01-01", "value": 17},
        ]
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_ind.id}).json()

        self.assertEqual(
            response["data"]["figureAggregations"]["idpsConflictFigures"],
            self._sorted_list_by_field(expected_data),
        )

    def test_idps_disaster_figures(self):
        expected_data = self._sorted_list_by_field(
            [
                {"date": "2021-09-12", "value": 4},
                {"date": "2022-01-01", "value": 13},
                {"date": "2022-08-17", "value": 5},
                {"date": "2022-12-12", "value": 11},
            ]
        )
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_nep.id}).json()
        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["idpsDisasterFigures"]),
            self._sorted_list_by_field(expected_data),
        )

        expected_data = [
            {"date": "2021-10-10", "value": 3},
            {"date": "2022-12-10", "value": 7},
            {"date": "2023-01-01", "value": 17},
        ]
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_ind.id}).json()

        self.assertEqual(
            self._sorted_list_by_field(expected_data),
            self._sorted_list_by_field(response["data"]["figureAggregations"]["idpsDisasterFigures"]),
        )

    def test_nds_conflict_figures(self):
        expected_data = [
            {"date": "2021-09-12", "value": 2},
            {"date": "2022-08-17", "value": 5},
            {"date": "2022-09-30", "value": 2},
            {"date": "2023-01-01", "value": 13},
            {"date": "2023-12-12", "value": 11},
        ]
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_nep.id}).json()
        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["ndsConflictFigures"]),
            self._sorted_list_by_field(expected_data),
        )

        expected_data = [
            {"date": "2022-12-10", "value": 7},
            {"date": "2023-01-01", "value": 17},
            {"date": "2023-09-30", "value": 3},
        ]
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_ind.id}).json()

        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["ndsConflictFigures"]),
            self._sorted_list_by_field(expected_data),
        )

    def test_nds_disaster_figures(self):
        expected_data = [
            {"date": "2021-09-12", "value": 2},
            {"date": "2022-08-17", "value": 5},
            {"date": "2022-09-30", "value": 2},
            {"date": "2023-01-01", "value": 13},
            {"date": "2023-12-12", "value": 11},
        ]
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_nep.id}).json()
        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["ndsDisasterFigures"]),
            self._sorted_list_by_field(expected_data),
        )

        expected_data = [
            {"date": "2022-12-10", "value": 7},
            {"date": "2023-01-01", "value": 17},
            {"date": "2023-09-30", "value": 3},
        ]
        response = self.query(self.aggregation_query, variables={"filterFigureCountries": self.country_ind.id}).json()
        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["ndsDisasterFigures"]),
            self._sorted_list_by_field(expected_data),
        )

    def test_figures_filtered_by_year(self):
        filter_data = {"filterFigureEndBefore": "2022-12-31", "filterFigureCountries": self.country_nep.id}
        response = self.query(self.aggregation_query, variables={**filter_data}).json()

        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["idpsConflictFigures"]),
            self._sorted_list_by_field(
                [
                    {"date": "2021-09-12", "value": 4},
                    {"date": "2022-08-17", "value": 5},
                ]
            ),
        )
        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["idpsDisasterFigures"]),
            self._sorted_list_by_field(
                [
                    {"date": "2021-09-12", "value": 4},
                    {"date": "2022-01-01", "value": 13},
                    {"date": "2022-08-17", "value": 5},
                    {"date": "2022-12-12", "value": 11},
                ]
            ),
        )
        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["ndsConflictFigures"]),
            self._sorted_list_by_field(
                [
                    {"date": "2021-09-12", "value": 2},
                    {"date": "2022-08-17", "value": 5},
                    {"date": "2022-09-30", "value": 2},
                ]
            ),
        )
        self.assertEqual(
            self._sorted_list_by_field(response["data"]["figureAggregations"]["ndsDisasterFigures"]),
            self._sorted_list_by_field(
                [
                    {"date": "2021-09-12", "value": 2},
                    {"date": "2022-08-17", "value": 5},
                    {"date": "2022-09-30", "value": 2},
                ]
            ),
        )
