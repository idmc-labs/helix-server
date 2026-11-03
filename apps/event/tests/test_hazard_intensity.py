"""U6.1 · Record how intense a hazard was on an event (A6.1.2: the seven optional event fields)."""

import json
from uuid import uuid4

from django.test import RequestFactory
from pydantic import ValidationError as PydanticValidationError

from apps.crisis.models import Crisis
from apps.event.filters import EventFilter
from apps.event.models import Event
from apps.event.serializers import EventSerializer
from apps.hulk.bulk.models import HulkEventImport
from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    DisasterSubTypeFactory,
    EventFactory,
)
from utils.tests import HelixGraphQLTestCase, HelixTestCase, create_user_with_role

HAZARD_FIELDS_GQL = """
    hazardIntensityValue
    hazardIntensityUnit
    hazardIntensityUnitDisplay
    hazardSourceName
    hazardSourceEventId
    hazardFootprintUrl
    hazardFootprintId
    hazardFootprintGeometryType
"""

FULL_HAZARD_INPUT = {
    "hazardIntensityValue": 7.8,
    "hazardIntensityUnit": "M",
    "hazardSourceName": "EMDAT",
    "hazardSourceEventId": "2016-0389-CHN",
    "hazardFootprintUrl": "https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=FL&eventid=1100137",
    "hazardFootprintId": "10177.0",
    "hazardFootprintGeometryType": "POLYGON",
}


class TestEventHazardMutations(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.country = CountryFactory.create()
        self.create_mutation = (
            """
            mutation CreateEvent($input: EventCreateInputType!) {
                createEvent(data: $input) {
                    ok
                    errors
                    result { id %s }
                }
            }
        """
            % HAZARD_FIELDS_GQL
        )
        self.update_mutation = (
            """
            mutation UpdateEvent($input: EventUpdateInputType!) {
                updateEvent(data: $input) {
                    ok
                    errors
                    result { id %s }
                }
            }
        """
            % HAZARD_FIELDS_GQL
        )
        self.base_input = {
            "name": "Earthquake",
            "eventType": "DISASTER",
            "disasterSubType": DisasterSubTypeFactory.create().id,
            "countries": [self.country.id],
            "startDate": "2016-01-01",
            "endDate": "2016-01-31",
            "eventNarrative": "event narrative",
        }
        self.force_login(create_user_with_role(USER_ROLE.MONITORING_EXPERT.name))

    def _create(self, **extra):
        response = self.query(self.create_mutation, input_data={**self.base_input, **extra})
        return response, json.loads(response.content)

    def test_event_without_hazard_fields_saves_unchanged(self):
        response, content = self._create()
        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["createEvent"]["ok"], content)
        result = content["data"]["createEvent"]["result"]
        for field in FULL_HAZARD_INPUT:
            self.assertIsNone(result[field], field)

    def test_event_with_all_hazard_fields(self):
        response, content = self._create(**FULL_HAZARD_INPUT)
        self.assertResponseNoErrors(response)
        self.assertTrue(content["data"]["createEvent"]["ok"], content)
        result = content["data"]["createEvent"]["result"]
        for field, value in FULL_HAZARD_INPUT.items():
            self.assertEqual(result[field], value, field)
        self.assertEqual(result["hazardIntensityUnitDisplay"], "M")

        event = Event.objects.get(pk=result["id"])
        self.assertEqual(event.hazard_intensity_unit, Event.HAZARD_INTENSITY_UNIT.M)
        self.assertEqual(event.hazard_footprint_geometry_type, Event.HAZARD_FOOTPRINT_GEOMETRY_TYPE.POLYGON)

    def test_update_without_hazard_fields_keeps_them(self):
        _, content = self._create(**FULL_HAZARD_INPUT)
        event_id = content["data"]["createEvent"]["result"]["id"]
        response = self.query(self.update_mutation, input_data={"id": event_id, "name": "Renamed"})
        content = json.loads(response.content)
        self.assertTrue(content["data"]["updateEvent"]["ok"], content)
        result = content["data"]["updateEvent"]["result"]
        for field, value in FULL_HAZARD_INPUT.items():
            self.assertEqual(result[field], value, field)

    def test_non_numeric_intensity_value_refused(self):
        count = Event.objects.count()
        response, content = self._create(hazardIntensityValue="7.8M")
        self.assertIsNotNone(content.get("errors"), content)
        self.assertEqual(Event.objects.count(), count)

    def test_unknown_geometry_type_refused(self):
        count = Event.objects.count()
        response, content = self._create(hazardFootprintGeometryType="CIRCLE")
        self.assertIsNotNone(content.get("errors"), content)
        self.assertEqual(Event.objects.count(), count)

    def test_unknown_unit_refused(self):
        count = Event.objects.count()
        response, content = self._create(hazardIntensityUnit="MPH")
        self.assertIsNotNone(content.get("errors"), content)
        self.assertEqual(Event.objects.count(), count)

    def test_invalid_footprint_url_refused(self):
        response, content = self._create(hazardFootprintUrl="not a url")
        self.assertFalse(content["data"]["createEvent"]["ok"], content)


class TestEventHazardSerializer(HelixTestCase):
    """The serializer is the gate shared by the form and the bulk import (Hulk calls createEvent)."""

    def setUp(self) -> None:
        request = RequestFactory().post("/graphql")
        request.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(request=request)
        self.data = {
            "name": "Cyclone",
            "event_type": Crisis.CRISIS_TYPE.DISASTER.value,
            "disaster_sub_type": DisasterSubTypeFactory.create().id,
            "countries": [CountryFactory.create().id],
            "start_date": "2016-01-01",
            "end_date": "2016-01-31",
            "event_narrative": "event narrative",
        }

    def _errors(self, **extra):
        serializer = EventSerializer(data={**self.data, **extra}, context=self.context)
        serializer.is_valid()
        return serializer.errors

    def test_valid_values(self):
        self.assertEqual(
            self._errors(
                hazard_intensity_value="185",
                hazard_intensity_unit=Event.HAZARD_INTENSITY_UNIT.KM_PER_HOUR.value,
                hazard_footprint_geometry_type=Event.HAZARD_FOOTPRINT_GEOMETRY_TYPE.MULTIPOLYGON.value,
            ),
            {},
        )

    def test_non_numeric_value_refused(self):
        for value in ["7.8M", "nan", "inf", "-inf", "185 km/h"]:
            self.assertIn("hazard_intensity_value", self._errors(hazard_intensity_value=value), value)

    def test_unknown_geometry_type_refused(self):
        self.assertIn("hazard_footprint_geometry_type", self._errors(hazard_footprint_geometry_type=99))


class TestHulkEventImportHazard(HelixTestCase):
    def _row(self, **overrides) -> dict:
        row = {
            "uuid": str(uuid4()),
            "event_name": "Earthquake",
            "event_cause": "DISASTER",
            "disaster_sub_type_id": DisasterSubTypeFactory.create().id,
            "start_date": "2016-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2016-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": "narrative",
            "countries_id": [CountryFactory.create().id],
            "event_codes": [],
        }
        row.update(overrides)
        return row

    def test_without_hazard_fields(self):
        payload = HulkEventImport(**self._row()).generate_for_graphql_mutation()
        self.assertIsNone(payload["hazardIntensityValue"])
        self.assertIsNone(payload["hazardIntensityUnit"])
        self.assertIsNone(payload["hazardFootprintGeometryType"])

    def test_blank_cells_are_treated_as_empty(self):
        payload = HulkEventImport(
            **self._row(hazard_intensity_value="", hazard_intensity_unit="", hazard_footprint_geometry_type=" ")
        ).generate_for_graphql_mutation()
        self.assertIsNone(payload["hazardIntensityValue"])
        self.assertIsNone(payload["hazardIntensityUnit"])
        self.assertIsNone(payload["hazardFootprintGeometryType"])

    def test_hazard_fields_reach_mutation_payload(self):
        payload = HulkEventImport(
            **self._row(
                hazard_intensity_value="7.8",
                hazard_intensity_unit="M",
                hazard_source_name="EMDAT",
                hazard_source_event_id="2016-0389-CHN",
                hazard_footprint_url="https://example.org/footprint.geojson",
                hazard_footprint_id="10177.0",
                hazard_footprint_geometry_type="polygon",
            )
        ).generate_for_graphql_mutation()
        self.assertEqual(payload["hazardIntensityValue"], 7.8)
        self.assertEqual(payload["hazardIntensityUnit"], "M")
        self.assertEqual(payload["hazardSourceName"], "EMDAT")
        self.assertEqual(payload["hazardSourceEventId"], "2016-0389-CHN")
        self.assertEqual(payload["hazardFootprintUrl"], "https://example.org/footprint.geojson")
        self.assertEqual(payload["hazardFootprintId"], "10177.0")
        self.assertEqual(payload["hazardFootprintGeometryType"], "POLYGON")

    def test_unit_accepts_label(self):
        payload = HulkEventImport(**self._row(hazard_intensity_unit="km/h")).generate_for_graphql_mutation()
        self.assertEqual(payload["hazardIntensityUnit"], "KM_PER_HOUR")

    def test_non_numeric_value_refused(self):
        for value in ["7.8M", "nan", "inf", True]:
            with self.assertRaises(PydanticValidationError, msg=value):
                HulkEventImport(**self._row(hazard_intensity_value=value))

    def test_unknown_geometry_type_refused(self):
        with self.assertRaises(PydanticValidationError):
            HulkEventImport(**self._row(hazard_footprint_geometry_type="CIRCLE"))


class TestEventHazardFilterAndExport(HelixTestCase):
    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.quake = EventFactory.create(
            hazard_intensity_value=7.8,
            hazard_intensity_unit=Event.HAZARD_INTENSITY_UNIT.M,
            hazard_source_name="EMDAT",
            hazard_source_event_id="2016-0389-CHN",
            hazard_footprint_url="https://example.org/footprint.geojson",
            hazard_footprint_id="10177.0",
            hazard_footprint_geometry_type=Event.HAZARD_FOOTPRINT_GEOMETRY_TYPE.POINT,
        )
        self.small_quake = EventFactory.create(
            hazard_intensity_value=4.1, hazard_intensity_unit=Event.HAZARD_INTENSITY_UNIT.M
        )
        self.cyclone = EventFactory.create(
            hazard_intensity_value=185, hazard_intensity_unit=Event.HAZARD_INTENSITY_UNIT.KM_PER_HOUR
        )
        self.no_intensity = EventFactory.create()

    def _filter(self, **data):
        class DummyRequest:
            user = self.user

        return set(EventFilter(data=data, request=DummyRequest()).qs.values_list("id", flat=True))

    def test_filter_by_value_range(self):
        self.assertEqual(self._filter(hazard_intensity_value__gte=7), {self.quake.id, self.cyclone.id})
        self.assertEqual(self._filter(hazard_intensity_value__lt=5), {self.small_quake.id})

    def test_filter_by_unit(self):
        self.assertEqual(self._filter(hazard_intensity_units=["M"]), {self.quake.id, self.small_quake.id})
        self.assertEqual(
            self._filter(hazard_intensity_units=["M"], hazard_intensity_value__gte=7),
            {self.quake.id},
        )
        self.assertEqual(self._filter(hazard_intensity_units=["KM_PER_HOUR"]), {self.cyclone.id})

    def test_export_has_the_seven_fields(self):
        sheet = Event.get_excel_sheets_data(self.user.id, {})
        headers = sheet["headers"]
        for key in [
            "hazard_intensity_value",
            "hazard_intensity_unit",
            "hazard_source_name",
            "hazard_source_event_id",
            "hazard_footprint_url",
            "hazard_footprint_id",
            "hazard_footprint_geometry_type",
        ]:
            self.assertIn(key, headers)

        rows = {row["id"]: sheet["transformer"](row) for row in sheet["data"]}
        quake = rows[self.quake.id]
        self.assertEqual(quake["hazard_intensity_value"], 7.8)
        self.assertEqual(str(quake["hazard_intensity_unit"]), "M")
        self.assertEqual(quake["hazard_source_name"], "EMDAT")
        self.assertEqual(quake["hazard_source_event_id"], "2016-0389-CHN")
        self.assertEqual(quake["hazard_footprint_url"], "https://example.org/footprint.geojson")
        self.assertEqual(quake["hazard_footprint_id"], "10177.0")
        self.assertEqual(str(quake["hazard_footprint_geometry_type"]), "POINT")
        self.assertEqual(str(rows[self.cyclone.id]["hazard_intensity_unit"]), "km/h")

        empty = rows[self.no_intensity.id]
        self.assertIsNone(empty["hazard_intensity_value"])
        self.assertEqual(empty["hazard_intensity_unit"], "")
        self.assertEqual(empty["hazard_footprint_geometry_type"], "")
