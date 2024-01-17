import json
from utils.tests import HelixGraphQLTestCase, create_user_with_role

from apps.users.enums import USER_ROLE
from apps.entry.models import (
    Figure,
)
from apps.crisis.models import Crisis
from utils.factories import (
    EventFactory,
    EntryFactory,
    FigureFactory,
    CountryFactory,
)


class TestFigureAggegationVisualization(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_nep = CountryFactory.create(name='Nepal', iso3='NPL')
        self.country_ind = CountryFactory.create(name='India', iso3='IND')
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)

    def test_figure_aggregation(self):
        query = '''
            query MyQuery (
                $filterFigureEntry: String
                $filterFigureContextOfViolence: [ID!]
                $filterEntryArticleTitle: String
                $filterEntryPublishers: [ID!]
                $filterFigureApprovedBy: [ID!]
                $filterFigureCategories: [String!]
                $filterFigureCategoryTypes: [String!]
                $filterFigureCountries: [ID!]
                $filterFigureCrises: [ID!]
                $filterFigureCrisisTypes: [String!]
                $filterFigureDisasterCategories: [ID!]
                $filterFigureDisasterSubCategories: [ID!]
                $filterFigureDisasterSubTypes: [ID!]
                $filterFigureDisasterTypes: [ID!]
                $filterFigureEndBefore: Date
                $filterFigureEvents: [ID!]
                $filterFigureGeographicalGroups: [ID!]
                $filterFigureHasDisaggregatedData: Boolean
                $filterFigureOsvSubTypes: [ID!]
                $filterFigureRegions: [ID!]
                $filterFigureReviewStatus: [String!]
                $filterFigureRoles: [String!]
                $filterFigureSources: [ID!]
                $filterFigureStartAfter: Date
                $filterFigureTags: [ID!]
                $filterFigureTerms: [ID!]
                $filterFigureViolenceSubTypes: [ID!]
                $filterFigureViolenceTypes: [ID!]
                $filterFigureHasExcerptIdu: Boolean
                $filterFigureHasHousingDestruction: Boolean
                $filterFigureIsToBeReviewed: Boolean
                $report: ID
            ) {
            figureAggregations(
                filters: {
                    filterFigureEntry: $filterFigureEntry
                    filterFigureContextOfViolence: $filterFigureContextOfViolence
                    filterEntryArticleTitle: $filterEntryArticleTitle
                    filterEntryPublishers: $filterEntryPublishers
                    filterFigureApprovedBy: $filterFigureApprovedBy
                    filterFigureCategories: $filterFigureCategories
                    filterFigureCategoryTypes: $filterFigureCategoryTypes
                    filterFigureCountries: $filterFigureCountries
                    filterFigureCrises: $filterFigureCrises
                    filterFigureCrisisTypes: $filterFigureCrisisTypes
                    filterFigureDisasterCategories: $filterFigureDisasterCategories
                    filterFigureDisasterSubCategories: $filterFigureDisasterSubCategories
                    filterFigureDisasterSubTypes: $filterFigureDisasterSubTypes
                    filterFigureDisasterTypes: $filterFigureDisasterTypes
                    filterFigureEndBefore: $filterFigureEndBefore
                    filterFigureEvents: $filterFigureEvents
                    filterFigureGeographicalGroups: $filterFigureGeographicalGroups
                    filterFigureHasDisaggregatedData: $filterFigureHasDisaggregatedData
                    filterFigureOsvSubTypes: $filterFigureOsvSubTypes
                    filterFigureRegions: $filterFigureRegions
                    filterFigureReviewStatus: $filterFigureReviewStatus
                    filterFigureRoles: $filterFigureRoles
                    filterFigureSources: $filterFigureSources
                    filterFigureStartAfter: $filterFigureStartAfter
                    filterFigureTags: $filterFigureTags
                    filterFigureTerms: $filterFigureTerms
                    filterFigureViolenceSubTypes: $filterFigureViolenceSubTypes
                    filterFigureViolenceTypes: $filterFigureViolenceTypes
                    filterFigureHasExcerptIdu: $filterFigureHasExcerptIdu
                    filterFigureHasHousingDestruction: $filterFigureHasHousingDestruction
                    filterFigureIsToBeReviewed: $filterFigureIsToBeReviewed
                    reportId: $report
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
        '''

        self.entry = EntryFactory.create()
        self.entry2 = EntryFactory.create()
        self.event = EventFactory.create()
        self.event2 = EventFactory.create()

        # Test for idpsConflictFigures
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=101,
            unit=Figure.UNIT.PERSON,
            end_date='2021-09-12'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2021-09-12'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2021-10-10'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=5,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2022-08-17'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=7,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2022-12-10'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=11,
            entry=self.entry,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2023-12-12'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=13,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2023-01-01'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=17,
            entry=self.entry,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2023-01-01'
        )

        self.force_login(self.admin)

        for filter_data, expected_data in [
            (
                {'filterFigureCountries': self.country_nep.id, },
                [
                    {
                        "date": "2021-09-12",
                        "value": 4
                    },
                    {
                        "date": "2022-08-17",
                        "value": 5
                    },
                    {
                        "date": "2023-01-01",
                        "value": 13
                    },
                    {
                        "date": "2023-12-12",
                        "value": 11
                    }
                ]
            ),
            (
                {'filterFigureCountries': self.country_ind.id, },
                [
                    {
                        "date": "2021-10-10",
                        "value": 3
                    },
                    {
                        "date": "2022-12-10",
                        "value": 7
                    },
                    {
                        "date": "2023-01-01",
                        "value": 17
                    },
                ]
            ),
        ]:
            response = self.query(query, variables={**filter_data}).json()

            self.assertEqual(
                response['data']['figureAggregations']['idpsConflictFigures'],
                expected_data,
            )

        # Test for idpsDisasterFigures
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=101,
            unit=Figure.UNIT.PERSON,
            start_date='2021-09-01',
            end_date='2021-09-12'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2020-09-01',
            end_date='2021-09-12'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2021-10-01',
            end_date='2021-10-10'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=5,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2022-08-01',
            end_date='2022-08-17'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=7,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2022-12-01',
            end_date='2022-12-10'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=11,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2021-12-12',
            end_date='2022-12-12'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=13,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2021-01-01',
            end_date='2022-01-01'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=17,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2022-01-01',
            end_date='2023-01-01',
        )

        for filter_data, expected_data in [
            (
                {'filterFigureCountries': self.country_nep.id, },
                [
                    {
                        "date": "2021-09-12",
                        "value": 4
                    },
                    {
                        "date": "2022-01-01",
                        "value": 13
                    },
                    {
                        "date": "2022-08-17",
                        "value": 5
                    },
                    {
                        "date": "2022-12-12",
                        "value": 11
                    },
                ]
            ),
            (
                {'filterFigureCountries': self.country_ind.id, },
                [
                    {
                        "date": "2021-10-10",
                        "value": 3
                    },
                    {
                        "date": "2022-12-10",
                        "value": 7
                    },
                    {
                        "date": "2023-01-01",
                        "value": 17
                    },
                ]
            )
        ]:
            response = self.query(query, variables={**filter_data})
            content = json.loads(response.content)
            self.assertEqual(
                content['data']['figureAggregations']['idpsDisasterFigures'], expected_data,
            )

        # Test for ndsConflictFigures
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=101,
            unit=Figure.UNIT.PERSON,
            start_date='2021-09-12',
            end_date='2021-09-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2021-09-12',
            end_date='2022-09-30'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2021-10-10',
            end_date='2023-09-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=5,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2022-08-17',
            end_date='2022-08-30'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=7,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2022-12-10',
            end_date='2022-12-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=11,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2023-12-12',
            end_date='2023-12-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=13,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2023-01-01',
            end_date='2023-12-30'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=17,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2023-01-01',
            end_date='2023-12-30',
        )

        for filter_data, expected_data in [
            (
                {'filterFigureCountries': self.country_nep.id, },
                [
                    {
                        "date": "2021-09-12",
                        "value": 2
                    },
                    {
                        "date": "2022-08-17",
                        "value": 5
                    },
                    {
                        "date": "2022-09-30",
                        "value": 2
                    },
                    {
                        "date": "2023-01-01",
                        "value": 13
                    },
                    {
                        "date": "2023-12-12",
                        "value": 11
                    }
                ]
            ),
            (
                {'filterFigureCountries': self.country_ind.id, },
                [
                    {
                        "date": "2022-12-10",
                        "value": 7
                    },
                    {
                        "date": "2023-01-01",
                        "value": 17
                    },
                    {
                        "date": "2023-09-30",
                        "value": 3
                    },
                ]
            )
        ]:
            response = self.query(query, variables={**filter_data})
            content = json.loads(response.content)
            self.assertEqual(
                content['data']['figureAggregations']['ndsConflictFigures'], expected_data,
            )

        # Test for ndsDisasterFigures
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=101,
            unit=Figure.UNIT.PERSON,
            start_date='2021-09-12',
            end_date='2021-09-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=2,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2021-09-12',
            end_date='2022-09-30'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            total_figures=3,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2021-10-10',
            end_date='2023-09-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=5,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2022-08-17',
            end_date='2022-08-30'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=7,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2022-12-10',
            end_date='2022-12-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=11,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2023-12-12',
            end_date='2023-12-30'
        )
        FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=13,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2023-01-01',
            end_date='2023-12-30'
        )
        FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.DISASTER,
            total_figures=17,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            reported=111,
            unit=Figure.UNIT.PERSON,
            start_date='2023-01-01',
            end_date='2023-12-30',
        )

        for filter_data, expected_data in [
            (
                {'filterFigureCountries': self.country_nep.id, },
                [
                    {
                        "date": "2021-09-12",
                        "value": 2
                    },
                    {
                        "date": "2022-08-17",
                        "value": 5
                    },
                    {
                        "date": "2022-09-30",
                        "value": 2
                    },
                    {
                        "date": "2023-01-01",
                        "value": 13
                    },
                    {
                        "date": "2023-12-12",
                        "value": 11
                    }
                ]
            ),
            (
                {'filterFigureCountries': self.country_ind.id, },
                [
                    {
                        "date": "2022-12-10",
                        "value": 7
                    },
                    {
                        "date": "2023-01-01",
                        "value": 17
                    },
                    {
                        "date": "2023-09-30",
                        "value": 3
                    },
                ]
            )
        ]:
            response = self.query(query, variables={**filter_data})
            content = json.loads(response.content)
            self.assertEqual(
                content['data']['figureAggregations']['ndsDisasterFigures'], expected_data,
            )

        # test filter by year
        filter_data = {
            "filterFigureEndBefore": '2022-12-31',
            'filterFigureCountries': self.country_nep.id
        }
        response = self.query(query, variables={**filter_data})
        content = json.loads(response.content)
        self.assertEqual(
            content['data']['figureAggregations']['idpsConflictFigures'],
            [
                {
                    "date": "2021-09-12",
                    "value": 4
                },
                {
                    "date": "2022-08-17",
                    "value": 5
                },

            ]
        )
        self.assertEqual(
            content['data']['figureAggregations']['idpsDisasterFigures'],
            [
                {
                    "date": "2021-09-12",
                    "value": 4
                },
                {
                    "date": "2022-01-01",
                    "value": 13
                },
                {
                    "date": "2022-08-17",
                    "value": 5
                },
                {
                    "date": "2022-12-12",
                    "value": 11
                },
            ]
        )
        self.assertEqual(
            content['data']['figureAggregations']['ndsConflictFigures'],
            [
                {
                    "date": "2021-09-12",
                    "value": 2
                },
                {
                    "date": "2022-08-17",
                    "value": 5
                },
                {
                    "date": "2022-09-30",
                    "value": 2
                },
            ]
        )
        self.assertEqual(
            content['data']['figureAggregations']['ndsDisasterFigures'],
            [
                {
                    "date": "2021-09-12",
                    "value": 2
                },
                {
                    "date": "2022-08-17",
                    "value": 5
                },
                {
                    "date": "2022-09-30",
                    "value": 2
                },
            ]
        )
