from copy import deepcopy as copy
from datetime import datetime, timedelta
from unittest.mock import call, patch
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.test import override_settings

from apps.crisis.models import Crisis
from apps.entry.models import Figure, FigureLocation
from apps.entry.mutations import BulkUpdateFigures
from apps.event.models import Event
from apps.notification.models import Notification
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    OrganizationFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role, snapshot_in_class  # noqa: F401


def clean_response(data):
    if isinstance(data, dict):
        for key in ["id", "uuid", "totalFlowNdFigures", "totalStockIdpFigures", "key"]:
            data.pop(key, None)
        for v in data.values():
            clean_response(v)
    elif isinstance(data, list):
        for item in data:
            clean_response(item)
    return data


def get_first_error_fields(errors):
    return [error["field"] for obj_errors in errors if obj_errors is not None for error in obj_errors]


@patch("apps.entry.mutations.BulkUpdateFigureManager.add_event")
@patch(
    "apps.entry.mutations.BulkUpdateFigureManager.__exit__",
    # Using side_effect to avoid suppressing exceptions
    side_effect=lambda *_: False,
)
class TestBulkFigureUpdate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country_1 = CountryFactory.create(iso2="JP", iso3="JPN")
        self.country_2 = CountryFactory.create(iso2="AF", iso3="AFC")
        self.event = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value, start_date="2015-01-01", end_date="2025-01-30"
        )
        self.event2 = EventFactory.create(
            event_type=Crisis.CRISIS_TYPE.DISASTER.value, start_date="2015-01-01", end_date="2025-01-30"
        )
        self.event.countries.add(self.country_1, self.country_2)
        self.event2.countries.add(self.country_1, self.country_2)
        self.fig_cat = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT
        self.editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.entry = EntryFactory.create(article_title="test", publish_date="2020-02-02")
        self.source = OrganizationFactory.create()
        self.violence_sub_type = ViolenceSubTypeFactory.create()

        self.f1, self.f2, self.f3 = FigureFactory.create_batch(3, event=self.event, entry=self.entry)

        self.geo_location_1 = {
            "uuid": str(uuid4()),
            "rank": 101,
            "country": "Japan",
            "countryCode": self.country_1.iso2,
            "osmId": "xxxx",
            "osmType": "yyyy",
            "displayName": "xxxx",
            "lat": 44,
            "lon": 44,
            "name": "Jp",
            "accuracy": FigureLocation.ACCURACY.ADM0.name,
            "identifier": FigureLocation.IDENTIFIER.ORIGIN.name,
            "geocoder": FigureLocation.GEOCODER.CUSTOM_SOURCE.name,
        }
        self.geo_location_2 = {
            "uuid": str(uuid4()),
            "rank": 10,
            "country": "Africa",
            "countryCode": self.country_2.iso2,
            "osmId": "hhh",
            "osmType": "kkk",
            "displayName": "jj",
            "lat": 55,
            "lon": 55,
            "name": "AFC",
            "accuracy": FigureLocation.ACCURACY.ADM0.name,
            "identifier": FigureLocation.IDENTIFIER.ORIGIN.name,
            "geocoder": FigureLocation.GEOCODER.CUSTOM_SOURCE.name,
        }
        self.figure_item_input = {
            "entry": self.entry.id,
            "uuid": str(uuid4()),
            "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.name,
            "includeIdu": False,
            "event": self.event.id,
            "reported": 50,
            "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
            "geoLocations": [self.geo_location_1],
            "country": self.country_1.id,
            "startDate": "2020-01-01",
            "endDate": "2020-01-30",
            "violenceSubType": self.violence_sub_type.id,
            "calculationLogic": "test logic",
            "unit": "PERSON",
            "category": "NEW_DISPLACEMENT",
            "term": "DISPLACED",
            "role": "RECOMMENDED",
            "sources": self.source.id,
            "tags": [],
        }

        self.figure_bulk_mutation = """
            mutation BulkUpdateFigures($items: [FigureUpdateInputType!], $delete_ids: [ID!]) {
                bulkUpdateFigures(items: $items, deleteIds: $delete_ids) {
                    errors
                    deletedResult {
                      id
                    }
                    result {
                      id
                      figureCause
                      includeIdu
                      unit
                      category
                      entry {
                        id
                        articleTitle
                      }
                      event {
                        id
                        name
                      }
                      term
                      unit
                      isHousingDestruction
                      displacementOccurredDisplay
                      displacementOccurred
                      endDateAccuracy
                      householdSize
                      disaggregationLocationCamp
                      disaggregationLocationNonCamp
                      disaggregationDisability
                      disaggregationIndigenousPeople
                      disaggregationDisplacementRural
                      disaggregationDisplacementUrban
                      disaggregationConflict
                      disaggregationConflictCommunal
                      disaggregationConflictCriminal
                      disaggregationConflictOther
                      disaggregationConflictPolitical
                      disaggregationSexFemale
                      disaggregationSexMale
                      disaggregationLgbtiq
                      disaggregationAge {
                        results {
                            id
                            ageFrom
                            ageTo
                            uuid
                            sex
                            value
                        }
                      }
                    }
                }
            }
        """
        self.force_login(self.editor)

    def assert_field_is_clear(self, fields, output):
        for field in fields:
            value = output[field]
            if isinstance(value, dict) and "results" in value:
                assert value["results"] in [None, []]
            else:
                assert value in [None, []]

    @pytest.mark.usefixtures("snapshot_in_class")
    def test_figure_validation_create(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        # country required
        f1 = self.figure_item_input.copy()
        f1.pop("country")

        # calculationLogic required
        f2 = self.figure_item_input.copy()
        f2.pop("calculationLogic")

        # quantifier required
        f3 = self.figure_item_input.copy()
        f3.pop("quantifier")

        # reported required
        f4 = self.figure_item_input.copy()
        f4.pop("reported")

        # event required
        f5 = self.figure_item_input.copy()
        f5.pop("event")

        # entry required
        f6 = self.figure_item_input.copy()
        f6.pop("entry")

        # tags cannot be null
        f7 = self.figure_item_input.copy()
        f7["tags"] = None

        # tags must be list of pk
        f8 = self.figure_item_input.copy()
        f8["tags"] = "string"

        # term required
        f9 = self.figure_item_input.copy()
        f9.pop("term")

        # category required
        f10 = self.figure_item_input.copy()
        f10.pop("category")

        # endDate required
        f11 = self.figure_item_input.copy()
        f11.pop("endDate")

        # endDate must be past date
        f12 = self.figure_item_input.copy()
        f12["endDate"] = (datetime.today() + timedelta(days=2)).date().isoformat()

        # unit required
        f13 = self.figure_item_input.copy()
        f13.pop("unit")

        # if unit = household, household size is required
        f14 = self.figure_item_input.copy()
        f14["unit"] = "HOUSEHOLD"
        f14["householdSize"] = None

        # figure_cause required
        f15 = self.figure_item_input.copy()
        f15.pop("figureCause")

        # if figureCause = Conflict, violenceSubType is required
        f16 = self.figure_item_input.copy()
        f16["figureCause"] = "CONFLICT"
        f16["violenceSubType"] = None

        # if figureCause = disaster, disasterSubType is required
        f17 = self.figure_item_input.copy()
        f17["figureCause"] = "DISASTER"
        f17["event"] = self.event2.id
        f17["disasterSubType"] = None

        # geoLocation must not be empty
        f18 = self.figure_item_input.copy()
        f18["geoLocations"] = []

        # lat should range between [-90, 90] (inclusive)
        f19 = self.figure_item_input.copy()
        geolocation_invalid_lat = self.geo_location_1.copy()
        geolocation_invalid_lat["lat"] = 100
        f19["geoLocations"] = [geolocation_invalid_lat]

        # lon should range between [-180, 180] (inclusive)
        f20 = self.figure_item_input.copy()
        geolocation_invalid_lon = self.geo_location_1.copy()
        geolocation_invalid_lon["lon"] = 200
        f20["geoLocations"] = [geolocation_invalid_lon]

        # if isDisaggregated = true, disaggregationAge is required
        f21 = self.figure_item_input.copy()
        f21["isDisaggregated"] = True
        f21["disaggregationAge"] = None

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        mock_bulk_update_figure_manager_exit.assert_called_once()
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        assert clean_response(content_data) == self.snapshot
        self.assertResponseNoErrors(response)

        # validate end data
        end_date_required_category_types = [
            Figure.FIGURE_CATEGORY_TYPES.IDPS.name,
            Figure.FIGURE_CATEGORY_TYPES.RETURNEES.name,
            Figure.FIGURE_CATEGORY_TYPES.LOCALLY_INTEGRATED_IDPS.name,
            Figure.FIGURE_CATEGORY_TYPES.IDPS_SETTLED_ELSEWHERE.name,
            Figure.FIGURE_CATEGORY_TYPES.PEOPLE_DISPLACED_ACROSS_BORDERS.name,
            Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK.name,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_STOCK.name,
        ]
        figures = []
        for category_type in end_date_required_category_types:
            figure = self.figure_item_input.copy()
            figure["category"] = category_type
            figure["endDate"] = None
            figures.append(figure)

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures,
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert clean_response(content_data) == self.snapshot
        self.assertResponseNoErrors(response)

        # end date must be past date
        end_date_must_be_past_date_categories = [
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.name,
            Figure.FIGURE_CATEGORY_TYPES.RETURN.name,
            Figure.FIGURE_CATEGORY_TYPES.MULTIPLE_DISPLACEMENT.name,
            Figure.FIGURE_CATEGORY_TYPES.PARTIAL_FLOW.name,
            Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_FLIGHT.name,
            Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_RETURN.name,
            Figure.FIGURE_CATEGORY_TYPES.RELOCATION_ELSEWHERE.name,
            Figure.FIGURE_CATEGORY_TYPES.DEATHS.name,
            Figure.FIGURE_CATEGORY_TYPES.PROVISIONAL_SOLUTIONS.name,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_LOCAL_INTEGRATION.name,
            Figure.FIGURE_CATEGORY_TYPES.LOCAL_INTEGRATION.name,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_RETURN_RETURNEE_DISPLACEMENT.name,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_RELOCATION_ELSEWHERE.name,
            Figure.FIGURE_CATEGORY_TYPES.BIRTH.name,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_FLOW.name,
            Figure.FIGURE_CATEGORY_TYPES.PEOPLE_DISPLACED_ACROSS_BORDERS_FLOW.name,
        ]
        figures_2 = []
        for category_type in end_date_must_be_past_date_categories:
            figure = self.figure_item_input.copy()
            figure["category"] = category_type
            figure["endDate"] = (datetime.today() + timedelta(days=2)).date().isoformat()
            figures_2.append(figure)

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures_2,
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert clean_response(content_data) == self.snapshot
        self.assertResponseNoErrors(response)

    @pytest.mark.usefixtures("snapshot_in_class")
    def test_figure_validation_update(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        # create a object for update
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [self.figure_item_input.copy()],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        mock_bulk_update_figure_manager_exit.assert_called_once()
        update_input_data = self.figure_item_input.copy()
        update_input_data["id"] = content_data["result"][0]["id"]

        # country required
        f1 = update_input_data.copy()
        f1.pop("country")

        # calculationLogic required
        f2 = update_input_data.copy()
        f2.pop("calculationLogic")

        # quantifier required
        f3 = update_input_data.copy()
        f3.pop("quantifier")

        # reported required
        f4 = update_input_data.copy()
        f4.pop("reported")

        # event required
        f5 = update_input_data.copy()
        f5.pop("event")

        # entry required
        f6 = update_input_data.copy()
        f6.pop("entry")

        # tags cannot be null
        f7 = update_input_data.copy()
        f7["tags"] = None

        # tags must be list of pk
        f8 = update_input_data.copy()
        f8["tags"] = "string"

        # term required
        f9 = update_input_data.copy()
        f9.pop("term")

        # category required
        f10 = update_input_data.copy()
        f10.pop("category")

        # endDate required
        f11 = update_input_data.copy()
        f11.pop("endDate")

        # endDate must be past date
        f12 = update_input_data.copy()
        f12["endDate"] = (datetime.today() + timedelta(days=2)).date().isoformat()

        # unit required
        f13 = update_input_data.copy()
        f13.pop("unit")

        # if unit = household, household size is required
        f14 = update_input_data.copy()
        f14["unit"] = "HOUSEHOLD"
        f14["householdSize"] = None

        # figure_cause required
        f15 = update_input_data.copy()
        f15.pop("figureCause")

        # if figureCause = Conflict, violenceSubType is required
        f16 = update_input_data.copy()
        f16["figureCause"] = "CONFLICT"
        f16["violenceSubType"] = None

        # if figureCause = disaster, disasterSubType is required
        f17 = update_input_data.copy()
        f17["figureCause"] = "DISASTER"
        f17["event"] = self.event2.id
        f17["disasterSubType"] = None

        # geoLocation must not be empty
        f18 = update_input_data.copy()
        f18["geoLocations"] = []

        # lat should range between [-90, 90] (inclusive)
        f19 = update_input_data.copy()
        geolocation_invalid_lat = self.geo_location_1.copy()
        geolocation_invalid_lat["lat"] = 100
        f19["geoLocations"] = [geolocation_invalid_lat]

        # lon should range between [-180, 180] (inclusive)
        f20 = update_input_data.copy()
        geolocation_invalid_lon = self.geo_location_1.copy()
        geolocation_invalid_lon["lon"] = 200
        f20["geoLocations"] = [geolocation_invalid_lon]

        # if isDisaggregated = true, disaggregationAge is required
        f21 = update_input_data.copy()
        f21["isDisaggregated"] = True
        f21["disaggregationAge"] = None

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14, f15, f16, f17, f18, f19, f20, f21],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert clean_response(content_data) == self.snapshot
        self.assertResponseNoErrors(response)

        # validate end data
        end_date_required_category_types = [
            Figure.FIGURE_CATEGORY_TYPES.IDPS.name,
            Figure.FIGURE_CATEGORY_TYPES.RETURNEES.name,
            Figure.FIGURE_CATEGORY_TYPES.LOCALLY_INTEGRATED_IDPS.name,
            Figure.FIGURE_CATEGORY_TYPES.IDPS_SETTLED_ELSEWHERE.name,
            Figure.FIGURE_CATEGORY_TYPES.PEOPLE_DISPLACED_ACROSS_BORDERS.name,
            Figure.FIGURE_CATEGORY_TYPES.PARTIAL_STOCK.name,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_STOCK.name,
        ]
        figures = []
        for category_type in end_date_required_category_types:
            figure = update_input_data.copy()
            figure["category"] = category_type
            figure["endDate"] = None
            figures.append(figure)

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures,
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert clean_response(content_data) == self.snapshot
        self.assertResponseNoErrors(response)

        # end date must be past date
        end_date_must_be_past_date_categories = [
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.name,
            Figure.FIGURE_CATEGORY_TYPES.RETURN.name,
            Figure.FIGURE_CATEGORY_TYPES.MULTIPLE_DISPLACEMENT.name,
            Figure.FIGURE_CATEGORY_TYPES.PARTIAL_FLOW.name,
            Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_FLIGHT.name,
            Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_RETURN.name,
            Figure.FIGURE_CATEGORY_TYPES.RELOCATION_ELSEWHERE.name,
            Figure.FIGURE_CATEGORY_TYPES.DEATHS.name,
            Figure.FIGURE_CATEGORY_TYPES.PROVISIONAL_SOLUTIONS.name,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_LOCAL_INTEGRATION.name,
            Figure.FIGURE_CATEGORY_TYPES.LOCAL_INTEGRATION.name,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_RETURN_RETURNEE_DISPLACEMENT.name,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_RELOCATION_ELSEWHERE.name,
            Figure.FIGURE_CATEGORY_TYPES.BIRTH.name,
            Figure.FIGURE_CATEGORY_TYPES.UNVERIFIED_FLOW.name,
            Figure.FIGURE_CATEGORY_TYPES.PEOPLE_DISPLACED_ACROSS_BORDERS_FLOW.name,
        ]
        figures_2 = []
        for category_type in end_date_must_be_past_date_categories:
            figure = update_input_data.copy()
            figure["category"] = category_type
            figure["endDate"] = (datetime.today() + timedelta(days=2)).date().isoformat()
            figures_2.append(figure)

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures_2,
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert clean_response(content_data) == self.snapshot
        self.assertResponseNoErrors(response)

    def test_field_is_cleared_create(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        """
        This test checks the field value in the response to be null or empty list
        """
        # if term equals distroyedHousing clear displacementOccured
        f1 = self.figure_item_input.copy()
        f1["term"] = "DESTROYED_HOUSING"

        # if term equals partiallyDistroyedHousing clear displacementOccured
        f2 = self.figure_item_input.copy()
        f2["term"] = "PARTIALLY_DESTROYED_HOUSING"

        # if term equals unihabitableHousing clear displacementOccured
        f3 = self.figure_item_input.copy()
        f3["term"] = "UNINHABITABLE_HOUSING"

        # if term equals evacuated clear isHousingDestruction
        f4 = self.figure_item_input.copy()
        f4["term"] = "EVACUATED"

        # if term equals displaced clear isHousingDestruction
        f5 = self.figure_item_input.copy()
        f5["term"] = "DISPLACED"

        # if term equals forcedToFlee clear isHousingDestruction
        f6 = self.figure_item_input.copy()
        f6["term"] = "FORCED_TO_FLEE"

        # if term equals relocated clear isHousingDestruction
        f7 = self.figure_item_input.copy()
        f7["term"] = "RELOCATED"

        # if term equals sheltered clear isHousingDestruction
        f8 = self.figure_item_input.copy()
        f8["term"] = "SHELTERED"

        # if term equals inReliefCamp clear isHousingDestruction
        f9 = self.figure_item_input.copy()
        f9["term"] = "IN_RELIEF_CAMP"

        # if term equals homeless clear isHousingDestruction, displacementOccurred
        f10 = self.figure_item_input.copy()
        f10["term"] = "HOMELESS"

        # if term equals affected clear isHousingDestruction, displacementOccurred
        f11 = self.figure_item_input.copy()
        f11["term"] = "AFFECTED"

        # if term equals returns clear isHousingDestruction, displacementOccurred
        f12 = self.figure_item_input.copy()
        f12["term"] = "RETURNS"

        # if term equals multipleOrOther clear isHousingDestruction, displacementOccurred
        f13 = self.figure_item_input.copy()
        f13["term"] = "MULTIPLE_OR_OTHER"

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        mock_bulk_update_figure_manager_exit.assert_called_once()

        expected_cleared_fields_for_term_input = {
            "DESTROYED_HOUSING": ["displacementOccurred"],
            "PARTIALLY_DESTROYED_HOUSING": ["displacementOccurred"],
            "UNINHABITABLE_HOUSING": ["displacementOccurred"],
            "EVACUATED": ["isHousingDestruction"],
            "DISPLACED": ["isHousingDestruction"],
            "FORCED_TO_FLEE": ["isHousingDestruction"],
            "RELOCATED": ["isHousingDestruction"],
            "SHELTERED": ["isHousingDestruction"],
            "IN_RELIEF_CAMP": ["isHousingDestruction"],
            "HOMELESS": ["isHousingDestruction", "displacementOccurredDisplay"],
            "AFFECTED": ["isHousingDestruction", "displacementOccurredDisplay"],
            "RETURNS": ["isHousingDestruction", "displacementOccurredDisplay"],
            "MULTIPLE_OR_OTHER": ["isHousingDestruction", "displacementOccurredDisplay"],
        }

        for item in content_data:
            self.assert_field_is_clear(expected_cleared_fields_for_term_input.get(item["term"]), item)

        # if category equals idps clear endDateAccuracy
        f14 = self.figure_item_input.copy()
        f14["category"] = "IDPS"

        # if category equals returnees clear endDateAccuracy
        f15 = self.figure_item_input.copy()
        f15["category"] = "RETURNEES"

        # if category equals locallyIntegratedIdps clear endDateAccuracy
        f16 = self.figure_item_input.copy()
        f16["category"] = "LOCALLY_INTEGRATED_IDPS"

        # if category equals idpsSettledElsewhere clear endDateAccuracy
        f17 = self.figure_item_input.copy()
        f17["category"] = "IDPS_SETTLED_ELSEWHERE"

        # if category equals peopleDisplacedAcrossBorders clear endDateAccuracy
        f18 = self.figure_item_input.copy()
        f18["category"] = "PEOPLE_DISPLACED_ACROSS_BORDERS"

        # if category equals partialStock clear endDateAccuracy
        f19 = self.figure_item_input.copy()
        f19["category"] = "PARTIAL_STOCK"

        # if category equals unverifiedStock clear endDateAccuracy
        f20 = self.figure_item_input.copy()
        f20["category"] = "UNVERIFIED_STOCK"

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [f14, f15, f16, f17, f18, f19, f20],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]

        expected_cleared_fields_for_category_input = {
            "IDPS": ["endDateAccuracy"],
            "RETURNEES": ["endDateAccuracy"],
            "LOCALLY_INTEGRATED_IDPS": ["endDateAccuracy"],
            "IDPS_SETTLED_ELSEWHERE": ["endDateAccuracy"],
            "PEOPLE_DISPLACED_ACROSS_BORDERS": ["endDateAccuracy"],
            "PARTIAL_STOCK": ["endDateAccuracy"],
            "UNVERIFIED_STOCK": ["endDateAccuracy"],
        }

        for item in content_data:
            self.assert_field_is_clear(expected_cleared_fields_for_category_input.get(item["category"]), item)

        # if unit not equals houseHold clear houseHoldSize
        f21 = self.figure_item_input.copy()
        f21["unit"] = "PERSON"

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [
                    f21,
                ],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]
        self.assert_field_is_clear(
            [
                "householdSize",
            ],
            content_data[0],
        )

        # if isDisaggregated equals false clear disaggregation fields
        f22 = self.figure_item_input.copy()
        f22["isDisaggregated"] = False
        f22["disaggregationLocationCamp"] = 1
        f22["disaggregationLocationNonCamp"] = 1
        f22["disaggregationDisability"] = 1
        f22["disaggregationIndigenousPeople"] = 1
        f22["disaggregationDisplacementRural"] = 1
        f22["disaggregationDisplacementUrban"] = 1
        f22["disaggregationAge"] = [
            {
                "uuid": "dd805252-639c-48db-aabc-ffb34dfe3ce4",
                "sex": "MALE",
                "value": 1,
                "ageFrom": 20,
                "ageTo": 20,
            }
        ]
        f22["disaggregationConflictCommunal"] = 1
        f22["disaggregationConflictCriminal"] = 1
        f22["disaggregationConflictOther"] = 1
        f22["disaggregationConflictPolitical"] = 1
        f22["disaggregationSexFemale"] = 1
        f22["disaggregationSexMale"] = 1
        f22["disaggregationLgbtiq"] = 1

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [
                    f22,
                ],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]

        self.assert_field_is_clear(
            [
                "disaggregationLocationCamp",
                "disaggregationLocationNonCamp",
                "disaggregationDisability",
                "disaggregationIndigenousPeople",
                "disaggregationDisplacementRural",
                "disaggregationDisplacementUrban",
                "disaggregationConflict",
                "disaggregationConflictCommunal",
                "disaggregationConflictCriminal",
                "disaggregationConflictOther",
                "disaggregationConflictPolitical",
                "disaggregationSexFemale",
                "disaggregationSexMale",
                "disaggregationLgbtiq",
                "disaggregationAge",
            ],
            content_data[0],
        )

    def test_field_is_cleared_update(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        """
        This test checks the field value in the response to be null or empty list
        """
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [self.figure_item_input],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        mock_bulk_update_figure_manager_exit.assert_called_once()
        update_data_input = self.figure_item_input.copy()
        update_data_input["id"] = content_data["result"][0]["id"]

        # if term equals distroyedHousing clear displacementOccured
        f1 = update_data_input
        f1["term"] = "DESTROYED_HOUSING"

        # if term equals partiallyDistroyedHousing clear displacementOccured
        f2 = update_data_input
        f2["term"] = "PARTIALLY_DESTROYED_HOUSING"

        # if term equals unihabitableHousing clear displacementOccured
        f3 = self.figure_item_input
        f3["term"] = "UNINHABITABLE_HOUSING"

        # if term equals evacuated clear isHousingDestruction
        f4 = self.figure_item_input
        f4["term"] = "EVACUATED"

        # if term equals displaced clear isHousingDestruction
        f5 = self.figure_item_input
        f5["term"] = "DISPLACED"

        # if term equals forcedToFlee clear isHousingDestruction
        f6 = self.figure_item_input
        f6["term"] = "FORCED_TO_FLEE"

        # if term equals relocated clear isHousingDestruction
        f7 = self.figure_item_input
        f7["term"] = "RELOCATED"

        # if term equals sheltered clear isHousingDestruction
        f8 = self.figure_item_input
        f8["term"] = "SHELTERED"

        # if term equals inReliefCamp clear isHousingDestruction
        f9 = self.figure_item_input
        f9["term"] = "IN_RELIEF_CAMP"

        # if term equals homeless clear isHousingDestruction, displacementOccurred
        f10 = self.figure_item_input
        f10["term"] = "HOMELESS"

        # if term equals affected clear isHousingDestruction, displacementOccurred
        f11 = self.figure_item_input
        f11["term"] = "AFFECTED"

        # if term equals returns clear isHousingDestruction, displacementOccurred
        f12 = self.figure_item_input
        f12["term"] = "RETURNS"

        # if term equals multipleOrOther clear isHousingDestruction, displacementOccurred
        f13 = self.figure_item_input
        f13["term"] = "MULTIPLE_OR_OTHER"

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]

        expected_cleared_fields_for_term_input = {
            "DESTROYED_HOUSING": ["displacementOccurred"],
            "PARTIALLY_DESTROYED_HOUSING": ["displacementOccurred"],
            "UNINHABITABLE_HOUSING": ["displacementOccured"],
            "EVACUATED": ["isHousingDestruction"],
            "DISPLACED": ["isHousingDestruction"],
            "FORCED_TO_FLEE": ["isHousingDestruction"],
            "RELOCATED": ["isHousingDestruction"],
            "SHELTERED": ["isHousingDestruction"],
            "IN_RELIEF_CAMP": ["isHousingDestruction"],
            "HOMELESS": ["isHousingDestruction", "displacementOccurredDisplay"],
            "AFFECTED": ["isHousingDestruction", "displacementOccurredDisplay"],
            "RETURNS": ["isHousingDestruction", "displacementOccurredDisplay"],
            "MULTIPLE_OR_OTHER": ["isHousingDestruction", "displacementOccurredDisplay"],
        }

        for item in content_data:
            self.assert_field_is_clear(expected_cleared_fields_for_term_input.get(item["term"]), item)

        # if category equals idps clear endDateAccuracy
        f14 = self.figure_item_input
        f14["category"] = "IDPS"

        # if category equals returnees clear endDateAccuracy
        f15 = self.figure_item_input
        f15["category"] = "RETURNEES"

        # if category equals locallyIntegratedIdps clear endDateAccuracy
        f16 = self.figure_item_input
        f16["category"] = "LOCALLY_INTEGRATED_IDPS"

        # if category equals idpsSettledElsewhere clear endDateAccuracy
        f17 = self.figure_item_input
        f17["category"] = "IDPS_SETTLED_ELSEWHERE"

        # if category equals peopleDisplacedAcrossBorders clear endDateAccuracy
        f18 = self.figure_item_input
        f18["category"] = "PEOPLE_DISPLACED_ACROSS_BORDERS"

        # if category equals partialStock clear endDateAccuracy
        f19 = self.figure_item_input
        f19["category"] = "PARTIAL_STOCK"

        # if category equals unverifiedStock clear endDateAccuracy
        f20 = self.figure_item_input
        f20["category"] = "UNVERIFIED_STOCK"

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [f14, f15, f16, f17, f18, f19, f20],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]

        expected_cleared_fields_for_category_input = {
            "IDPS": ["endDateAccuracy"],
            "RETURNEES": ["endDateAccuracy"],
            "LOCALLY_INTEGRATED_IDPS": ["endDateAccuracy"],
            "IDPS_SETTLED_ELSEWHERE": ["endDateAccuracy"],
            "PEOPLE_DISPLACED_ACROSS_BORDERS": ["endDateAccuracy"],
            "PARTIAL_STOCK": ["endDateAccuracy"],
            "UNVERIFIED_STOCK": ["endDateAccuracy"],
        }

        for item in content_data:
            self.assert_field_is_clear(expected_cleared_fields_for_category_input.get(item["category"]), item)

        # if unit not equals houseHold clear houseHoldSize
        f21 = self.figure_item_input
        f21["unit"] = "PERSON"

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [
                    f21,
                ],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]
        self.assert_field_is_clear(
            [
                "householdSize",
            ],
            content_data[0],
        )

        # if isDisaggregated equals false clear disaggregation fields
        f22 = self.figure_item_input
        f22["isDisaggregated"] = False
        f22["disaggregationLocationCamp"] = 1
        f22["disaggregationLocationNonCamp"] = 1
        f22["disaggregationDisability"] = 1
        f22["disaggregationIndigenousPeople"] = 1
        f22["disaggregationDisplacementRural"] = 1
        f22["disaggregationDisplacementUrban"] = 1
        f22["disaggregationAge"] = [
            {
                "uuid": "dd805252-639c-48db-aabc-ffb34dfe3ce4",
                "sex": "MALE",
                "value": 1,
                "ageFrom": 20,
                "ageTo": 20,
            }
        ]
        f22["disaggregationConflictCommunal"] = 1
        f22["disaggregationConflictCriminal"] = 1
        f22["disaggregationConflictOther"] = 1
        f22["disaggregationConflictPolitical"] = 1
        f22["disaggregationSexFemale"] = 1
        f22["disaggregationSexMale"] = 1
        f22["disaggregationLgbtiq"] = 1

        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [
                    f22,
                ],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]["result"]

        self.assert_field_is_clear(
            [
                "disaggregationLocationCamp",
                "disaggregationLocationNonCamp",
                "disaggregationDisability",
                "disaggregationIndigenousPeople",
                "disaggregationDisplacementRural",
                "disaggregationDisplacementUrban",
                "disaggregationConflict",
                "disaggregationConflictCommunal",
                "disaggregationConflictCriminal",
                "disaggregationConflictOther",
                "disaggregationConflictPolitical",
                "disaggregationSexFemale",
                "disaggregationSexMale",
                "disaggregationLgbtiq",
                "disaggregationAge",
            ],
            content_data[0],
        )

    def test_can_bulk_create_and_delete_figures(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        figures = [
            {
                "uuid": str(uuid4()),
                "country": self.country_1.id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.name,
                "reported": 100,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.FIGURE_TERMS.EVACUATED.name,
                "category": self.fig_cat.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2019-10-10",
                "includeIdu": True,
                "excerptIdu": "example xxx",
                "geoLocations": [self.geo_location_1],
                "calculationLogic": "test test logic",
                "sourceExcerpt": "source test excerpt",
                "event": self.event.id,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "entry": self.entry.id,
                "sources": [self.source.id],
                "endDate": "2019-10-30",
                "violenceSubType": self.violence_sub_type.id,
            },
            {
                "uuid": str(uuid4()),
                "country": self.country_2.id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.name,
                "reported": 300,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.FIGURE_TERMS.EVACUATED.name,
                "category": self.fig_cat.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2020-10-10",
                "includeIdu": True,
                "excerptIdu": "excerpt for test",
                "geoLocations": [self.geo_location_2],
                "calculationLogic": "test check logics",
                "sourceExcerpt": "source excerpt content",
                "event": self.event.id,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "entry": self.entry.id,
                "sources": [self.source.id],
                "endDate": "2020-10-30",
                "violenceSubType": self.violence_sub_type.id,
            },
            {
                "uuid": str(uuid4()),
                "country": self.country_1.id,
                "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.name,
                "reported": 500,
                "unit": Figure.UNIT.PERSON.name,
                "term": Figure.FIGURE_TERMS.EVACUATED.name,
                "category": self.fig_cat.name,
                "role": Figure.ROLE.RECOMMENDED.name,
                "startDate": "2022-10-10",
                "includeIdu": True,
                "excerptIdu": "test excerpt ....",
                "geoLocations": [self.geo_location_1],
                "calculationLogic": "test logics ...",
                "sourceExcerpt": "source excerpt ...",
                "event": self.event.id,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "entry": self.entry.id,
                "sources": [self.source.id],
                "endDate": "2022-10-30",
                "violenceSubType": self.violence_sub_type.id,
            },
        ]

        figure_ids = [self.f1.id, self.f2.id, self.f3.id]
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures,
                "delete_ids": figure_ids,
            },
        )

        # Test created
        content_data = response.json()["data"]["bulkUpdateFigures"]
        self.assertResponseNoErrors(response)
        self.assertEqual(content_data["errors"], [None] * 3)
        self.assertEqual(len(content_data["result"]), 3)
        self.assertNotIn(None, content_data["result"])
        self.assertEqual(len(content_data["deletedResult"]), len(figure_ids), content_data)
        assert mock_bulk_update_figure_manager_add_event.call_count == 6
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        mock_bulk_update_figure_manager_exit.assert_called_once()

        # Test bulk deleted
        self.assertEqual(Figure.objects.filter(id__in=figure_ids).count(), 0)

        # Check each item
        for created_figure in content_data["result"]:
            self.assertEqual(created_figure["figureCause"], Crisis.CRISIS_TYPE.CONFLICT.name)
            self.assertEqual(created_figure["includeIdu"], True)
            self.assertEqual(created_figure["entry"]["id"], str(self.entry.id))

    def test_can_bulk_update_and_delete_figures(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        figures = [
            {
                "id": self.f1.id,
                "entry": self.entry.id,
                "uuid": str(uuid4()),
                "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.name,
                "includeIdu": False,
                "event": self.event.id,
                "reported": 1000,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "geoLocations": [self.geo_location_1],
                "country": self.country_1.id,
                "category": Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.name,
                "startDate": "2025-01-05",
                "endDate": "2025-01-10",
                "violenceSubType": self.violence_sub_type.id,
            },
            {
                "id": self.f2.id,
                "entry": self.entry.id,
                "uuid": str(uuid4()),
                "quantifier": Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.name,
                "includeIdu": False,
                "event": self.event.id,
                "reported": 1000,
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "geoLocations": [self.geo_location_1],
                "country": self.country_1.id,
                "category": Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.name,
                "startDate": "2025-01-05",
                "endDate": "2025-01-10",
                "violenceSubType": self.violence_sub_type.id,
            },
        ]
        figure_ids = [self.f3.id]
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": figures,
                "delete_ids": figure_ids,
            },
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 3
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        mock_bulk_update_figure_manager_exit.assert_called_once()

        # Test bulk deleted
        self.assertEqual(Figure.objects.filter(id__in=figure_ids).count(), 0)

        # Test updated
        content_data = response.json()["data"]["bulkUpdateFigures"]
        self.assertResponseNoErrors(response)
        self.assertEqual(content_data["errors"], [None] * 2)
        self.assertEqual(len(content_data["result"]), 2)
        self.assertNotIn(None, content_data["result"])
        assert None not in content_data["result"]

        # Check each item
        for updated_figure in content_data["result"]:
            self.assertEqual(updated_figure["figureCause"], Crisis.CRISIS_TYPE.CONFLICT.name)
            self.assertEqual(updated_figure["includeIdu"], False)
            self.assertEqual(updated_figure["entry"]["id"], str(self.entry.id))

    def test_household_size_validation(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        """
        reported <= disaggregationLocationCamp + disaggregationLocationNonCamp
        """
        figure_item_input = copy(self.figure_item_input)
        figure_item_input.update(
            {
                "reported": 30,
                "isDisaggregated": True,
                "disaggregationLocationCamp": 200,
                "disaggregationLocationNonCamp": 10,
            }
        )
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            },
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 0
        assert mock_bulk_update_figure_manager_exit.call_count == 1
        content_data = response.json()["data"]["bulkUpdateFigures"]
        self.assertIn("disaggregationLocationCamp", get_first_error_fields(content_data["errors"]))
        self.assertIn("disaggregationLocationNonCamp", get_first_error_fields(content_data["errors"]))

        figure_item_input.update(
            {
                "reported": 300,
                "disaggregationLocationCamp": 200,
                "disaggregationLocationNonCamp": 100,
            }
        )
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            },
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 1
        mock_bulk_update_figure_manager_add_event.assert_has_calls([call(self.event.id)])
        assert mock_bulk_update_figure_manager_exit.call_count == 2
        content_data = response.json()["data"]["bulkUpdateFigures"]

    def test_invalid_figures_household_size(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        """
        If unit is househod, household_size must be supplied.
        """
        self.f3.household_size = None
        self.f3.save()

        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [
                    {
                        **self.figure_item_input,
                        "unit": Figure.UNIT.HOUSEHOLD.name,
                    }
                ],
                "delete_ids": [],
            },
        )
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_called_once()
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert "householdSize" in get_first_error_fields(content_data["errors"])

    def test_invalid_figures_age_data(
        self,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        figure_item_input = copy(self.figure_item_input)
        figure_item_input.update(
            {
                "isDisaggregated": True,
                "disaggregationAge": [
                    # invalid: category and sex is duplicated
                    {"uuid": "e4857d07-736c-4ff3-a21f-51170f0551c9", "ageFrom": 10, "ageTo": 20, "sex": "MALE", "value": 5},
                    {"uuid": "4c3dd257-30b1-4f62-8f3a-e90e8ac57bce", "ageFrom": 10, "ageTo": 20, "sex": "MALE", "value": 5},
                ],
            }
        )
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_not_called()
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            },
        )
        mock_bulk_update_figure_manager_add_event.assert_not_called()
        mock_bulk_update_figure_manager_exit.assert_called_once()
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert content_data["result"] == [None]
        assert "disaggregationAge" in get_first_error_fields(content_data["errors"])

    def test_figure_cause_should_be_same_as_event_type(self, *_):
        event_1 = EventFactory.create(event_type=Crisis.CRISIS_TYPE.CONFLICT)
        event_2 = EventFactory.create(event_type=Crisis.CRISIS_TYPE.DISASTER)
        event_3 = EventFactory.create(event_type=Crisis.CRISIS_TYPE.OTHER)

        # Make copies of input
        figure_input_1 = copy(self.figure_item_input)
        figure_input_2 = copy(self.figure_item_input)
        figure_input_3 = copy(self.figure_item_input)

        # Pass incorrect figure cause and test
        figure_input_1.update(
            {
                "figureCause": Crisis.CRISIS_TYPE.DISASTER.name,
                "event": event_1.id,
            }
        )
        figure_input_2.update(
            {
                "figureCause": Crisis.CRISIS_TYPE.OTHER.name,
                "event": event_2.id,
            }
        )
        figure_input_3.update(
            {
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "event": event_3.id,
            }
        )
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_input_1, figure_input_2, figure_input_3],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        self.assertResponseNoErrors(response)
        assert "figureCause" in get_first_error_fields(content_data["errors"])

        # Pass correct figure cause and test
        figure_input_1.update(
            {
                "figureCause": Crisis.CRISIS_TYPE.CONFLICT.name,
                "event": event_1.id,
            }
        )
        figure_input_2.update(
            {
                "figureCause": Crisis.CRISIS_TYPE.DISASTER.name,
                "event": event_2.id,
            }
        )
        figure_input_3.update(
            {
                "figureCause": Crisis.CRISIS_TYPE.OTHER.name,
                "event": event_3.id,
            }
        )
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_input_1, figure_input_2, figure_input_3],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        self.assertResponseNoErrors(response)
        assert "figureCause" not in get_first_error_fields(content_data["errors"])

    def test_figure_include_idu_validation(self, *_):
        """
        If includeIdu is True, excerptIdu must be provided.
        """
        # Pass invalid input and test
        figure_item_input = copy(self.figure_item_input)
        figure_item_input.update(
            {
                "includeIdu": True,
                "excerptIdu": "  ",
            }
        )
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert "excerptIdu" in get_first_error_fields(content_data["errors"])

        # Pass correct value and test
        figure_item_input.update(
            {
                "includeIdu": False,
                "excerptIdu": "  ",
            }
        )
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_item_input],
                "delete_ids": [],
            },
        )
        content_data = response.json()["data"]["bulkUpdateFigures"]
        assert "excerptIdu" not in get_first_error_fields(content_data["errors"])

    @patch("apps.entry.serializers.send_figure_notifications")
    def test_should_update_event_in_figure(
        self,
        serializer_notification_send,
        mock_bulk_update_figure_manager_exit,
        mock_bulk_update_figure_manager_add_event,
    ):
        entry = EntryFactory.create()
        event1, event2, event3 = EventFactory.create_batch(
            3,
            countries=[self.country_1],
            review_status=Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
        )
        figure1 = FigureFactory.create(entry=entry, event=event1)
        figure2 = FigureFactory.create(entry=entry, event=event2)

        def _get_mock_call_arg(mock):
            return [
                (
                    call.args[0].id,  # Figure
                    call.args[1].id,  # User
                    call.args[2],  # Type
                )
                for call in mock.mock_calls
            ]

        def _reset_mock():
            mock_bulk_update_figure_manager_add_event.reset_mock()
            mock_bulk_update_figure_manager_exit.reset_mock()
            serializer_notification_send.reset_mock()

        for _event in [event1, event2, event3]:
            _event.countries.add(self.country_1, self.country_2)

        # Make copies of input
        figure_input_1 = copy(self.figure_item_input)
        figure_input_2 = copy(self.figure_item_input)

        # Test with correct event ids
        figure_input_1.update({"id": figure1.id, "event": event1.id, "violenceSubType": self.violence_sub_type.id})
        figure_input_2.update({"id": figure2.id, "event": event2.id, "violenceSubType": self.violence_sub_type.id})
        response = self.query(
            self.figure_bulk_mutation,
            variables={
                "items": [figure_input_1, figure_input_2],
                "delete_ids": [],
            },
        )
        assert mock_bulk_update_figure_manager_add_event.call_count == 2
        mock_bulk_update_figure_manager_add_event.assert_has_calls(
            [
                call(event1.id),
                call(event2.id),
            ],
            any_order=True,
        )
        mock_bulk_update_figure_manager_exit.assert_called_once()
        self.assertResponseNoErrors(response)
        content_data = response.json()["data"]["bulkUpdateFigures"]
        self.assertNotIn("event", get_first_error_fields(content_data["errors"]))
        self.assertNotEqual(content_data["result"], [None, None])
        # Notification check - Should be empty
        assert serializer_notification_send.call_count == 2
        assert _get_mock_call_arg(serializer_notification_send) == [
            (figure1.pk, self.editor.id, Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT),
            (figure2.pk, self.editor.id, Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT),
        ]
        _reset_mock()

        for event_review_status, have_figure_move_notification in [
            [Event.EVENT_REVIEW_STATUS.SIGNED_OFF, True],
            [Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED, True],
            [Event.EVENT_REVIEW_STATUS.APPROVED, True],
            [Event.EVENT_REVIEW_STATUS.APPROVED, True],
            [Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED, True],
            [Event.EVENT_REVIEW_STATUS.REVIEW_NOT_STARTED, False],
            [Event.EVENT_REVIEW_STATUS.REVIEW_IN_PROGRESS, False],
        ]:
            # Change event status
            for event in [event1, event2, event3]:
                event.review_status = event_review_status
                event.save()
            # Rest figure2 event to event2
            figure2.event = event2
            figure2.save()
            # Test with changed event ids
            figure_input_1.update(
                {
                    "id": figure1.id,
                    "event": event1.id,
                }
            )
            figure_input_2.update(
                {
                    "id": figure2.id,
                    "event": event3.id,
                }
            )
            response = self.query(
                self.figure_bulk_mutation,
                variables={
                    "items": [figure_input_1, figure_input_2],
                    "delete_ids": [],
                },
            )
            self.assertResponseNoErrors(response)
            assert mock_bulk_update_figure_manager_add_event.call_count == 3
            mock_bulk_update_figure_manager_add_event.assert_has_calls(
                [
                    # Figure 1 - Figure changed
                    call(event1.id),
                    # Figure 2 - Figure moved
                    call(event2.id),  # Existing event
                    call(event3.id),  # New event
                ]
            )
            # Notification check
            if have_figure_move_notification:
                notification_types = (
                    (
                        Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT,
                        Notification.Type.FIGURE_CREATED_IN_SIGNED_EVENT,
                        Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT,
                    )
                    if event_review_status
                    in [
                        Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
                        Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
                    ]
                    else (
                        Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT,
                        Notification.Type.FIGURE_CREATED_IN_APPROVED_EVENT,
                        Notification.Type.FIGURE_UPDATED_IN_APPROVED_EVENT,
                    )
                )
                assert _get_mock_call_arg(serializer_notification_send) == [
                    (figure1.pk, self.editor.id, notification_types[2]),
                    # Deleted in event2
                    (figure2.pk, self.editor.id, notification_types[0]),
                    # Created in event2
                    (figure2.pk, self.editor.id, notification_types[1]),
                ]
            else:
                assert _get_mock_call_arg(serializer_notification_send) == []
            mock_bulk_update_figure_manager_exit.assert_called_once()
            _reset_mock()

        content_data = response.json()["data"]["bulkUpdateFigures"]
        self.assertNotIn("event", get_first_error_fields(content_data["errors"]))
        self.assertEqual(str(event1.id), content_data["result"][0]["event"]["id"])
        self.assertEqual(event1.name, content_data["result"][0]["event"]["name"])
        self.assertEqual(str(event3.id), content_data["result"][1]["event"]["id"])
        self.assertEqual(event3.name, content_data["result"][1]["event"]["name"])

    def test_bulk_update_batch_size(self, *_):
        figure_item_input = copy(self.figure_item_input)
        payload = {
            "items": [figure_item_input] * 3,
            "delete_ids": [1, 2],
        }
        with override_settings(GRAPHENE_BATCH_DEFAULT_MAX_LIMIT=4):
            response = self.query(self.figure_bulk_mutation, variables=payload)
            content_data = response.json()["data"]["bulkUpdateFigures"]
            self.assertResponseErrors(response)
            assert content_data is None
            # Unit test
            with self.assertRaises(PermissionDenied) as exc:
                BulkUpdateFigures.validate_batch_size([1] * 3, [1, 2])
            assert str(exc.exception) == (
                "Max limit for batch is 4. But 5 where provided. Where CREATE/UPDATE = 3 and DELETE = 2"
            )
        with override_settings(GRAPHENE_BATCH_DEFAULT_MAX_LIMIT=6):
            response = self.query(self.figure_bulk_mutation, variables=payload)
            content_data = response.json()["data"]["bulkUpdateFigures"]
            self.assertResponseNoErrors(response)
            assert content_data is not None
            # Unit test
            BulkUpdateFigures.validate_batch_size([1] * 3, [1, 2])

    @patch("apps.entry.mutations.send_figure_notifications")
    @patch("apps.entry.serializers.send_figure_notifications")
    def test_bulk_update_notification_test(self, serializer_send, mutation_send, *_):
        figure_item_input = copy(self.figure_item_input)
        figure_item_input["id"] = self.f3.id
        payload = {
            "items": [figure_item_input] * 3,  # Change fig3 only
            "delete_ids": [self.f1.pk, self.f2.pk],
        }
        self.event.review_status = Event.EVENT_REVIEW_STATUS.SIGNED_OFF
        self.event.save()
        response = self.query(self.figure_bulk_mutation, variables=payload)
        self.assertResponseNoErrors(response)

        def _get_mock_call_arg(mock):
            return [
                (
                    call.args[0].id,  # Figure
                    call.args[1].id,  # User
                    call.args[2],  # Type
                )
                for call in mock.mock_calls
            ]

        # Check
        # -- Call within serializer (Update)
        assert _get_mock_call_arg(serializer_send) == [
            (
                item["id"],
                self.editor.id,
                Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT,
            )
            for item in payload["items"]
        ]
        # -- Call within mutation class (Delete)
        assert _get_mock_call_arg(mutation_send) == [
            (
                id,
                self.editor.id,
                Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT,
            )
            for id in payload["delete_ids"]
        ]
