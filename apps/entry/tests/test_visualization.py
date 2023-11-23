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
    OrganizationFactory,
    CountryFactory,
    TagFactory,
    ContextOfViolenceFactory,
)


class TestFigureAggegationVisualization(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_nep = CountryFactory.create(name='Nepal', iso3='NPL')
        self.country_ind = CountryFactory.create(name='India', iso3='IND')
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)

    def test_figure_aggregation(self):
        query = '''
            query MyQuery (
                $entry: ID
                $event: String
                $filterContextOfViolences: [ID!]
                $filterCreatedBy: [ID!]
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
                $filterFigureGlideNumber: [String!]
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
                $filterHasExcerptIdu: Boolean
                $filterHasHousingDestruction: Boolean
                $filterIsFigureToBeReviewed: Boolean
                $report: String
            ) {
            figureAggregations(
                entry: $entry
                event: $event
                filterContextOfViolences: $filterContextOfViolences
                filterCreatedBy: $filterCreatedBy
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
                filterFigureGlideNumber: $filterFigureGlideNumber
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
                filterHasExcerptIdu: $filterHasExcerptIdu
                filterHasHousingDestruction: $filterHasHousingDestruction
                filterIsFigureToBeReviewed: $filterIsFigureToBeReviewed
                report: $report
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
        self.stock_fig_cat = Figure.FIGURE_CATEGORY_TYPES.IDPS

        figure1 = FigureFactory.create(
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
        figure2 = FigureFactory.create(
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
        figure3 = FigureFactory.create(
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
        figure4 = FigureFactory.create(
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
        figure5 = FigureFactory.create(
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
        figure6 = FigureFactory.create(
            country=self.country_nep,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=11,
            entry=self.entry2,
            event=self.event2,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            reported=111,
            unit=Figure.UNIT.PERSON,
            end_date='2023-12-12'
        )
        figure7 = FigureFactory.create(
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
        figure8 = FigureFactory.create(
            country=self.country_ind,
            role=Figure.ROLE.RECOMMENDED,
            figure_cause=Crisis.CRISIS_TYPE.CONFLICT,
            total_figures=17,
            entry=self.entry2,
            event=self.event2,
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
        ]:
            response = self.query(query, variables={**filter_data})
            content = json.loads(response.content)
            self.assertEqual(
                content['data']['figureAggregations']['idpsConflictFigures'], expected_data,
            )
