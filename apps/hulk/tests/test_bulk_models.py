"""
Tests for the ``apps.hulk.bulk.models`` pydantic models — the layer that
converts JSONL input rows into the dict shape sent to helix GraphQL mutations
via ``generate_for_graphql_mutation``.
"""

from __future__ import annotations

import datetime
import types
from uuid import UUID

from pydantic import ValidationError
from pyhelix import models as pyhelix_models
from pyhelix.api.api import helix_client_context

from apps.hulk.bulk.models import HulkEventImport, HulkEventImportEventCode
from utils.factories import (
    CountryFactory,
    DisasterSubTypeFactory,
    ViolenceSubTypeFactory,
)
from utils.tests import HelixGraphQLTestCase


class TestHulkEventImportEventCodes(HelixGraphQLTestCase):
    """``event_codes`` must reach the mutation payload — until recently it was
    hardcoded to ``[]`` regardless of input."""

    def _event_row(self, **overrides) -> dict:
        country = CountryFactory.create()
        violence_sub_type = ViolenceSubTypeFactory.create()
        row = {
            "uuid": "11111111-1111-1111-1111-111111111111",
            "event_name": "Test event",
            "event_cause": "CONFLICT",
            "violence_sub_type_id": violence_sub_type.id,
            "disaster_sub_type_id": None,
            "other_sub_type_id": None,
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": "narrative",
            "countries_id": [country.id],
            "event_codes": [],
        }
        row.update(overrides)
        return row

    def test_empty_event_codes_emit_empty_list(self):
        payload = HulkEventImport(**self._event_row()).generate_for_graphql_mutation()
        self.assertEqual(payload["eventCodes"], [])

    def test_event_codes_passed_through_to_mutation_payload(self):
        country = CountryFactory.create()
        ec_uuid = UUID("22222222-2222-2222-2222-222222222222")
        row = self._event_row(
            event_codes=[
                {
                    "uuid": str(ec_uuid),
                    "country_id": country.id,
                    "event_code": "GLD-001",
                    "event_code_type": "GLIDE_NUMBER",
                }
            ]
        )
        payload = HulkEventImport(**row).generate_for_graphql_mutation()
        self.assertEqual(
            payload["eventCodes"],
            [
                {
                    "uuid": str(ec_uuid),
                    "country": country.id,
                    "eventCode": "GLD-001",
                    "eventCodeType": "GLIDE_NUMBER",
                }
            ],
        )

    def test_disaster_event_codes_passed_through(self):
        """``event_cause=DISASTER`` takes a different validator branch but the
        event_codes wiring must still produce the list."""
        country = CountryFactory.create()
        disaster_sub_type = DisasterSubTypeFactory.create()
        ec_uuid = UUID("33333333-3333-3333-3333-333333333333")
        row = self._event_row(
            event_cause="DISASTER",
            violence_sub_type_id=None,
            disaster_sub_type_id=disaster_sub_type.id,
            event_codes=[
                {
                    "uuid": str(ec_uuid),
                    "country_id": country.id,
                    "event_code": "GOV-77",
                    "event_code_type": "GOV_ASSIGNED_IDENTIFIER",
                }
            ],
        )
        payload = HulkEventImport(**row).generate_for_graphql_mutation()
        self.assertEqual(len(payload["eventCodes"]), 1)
        self.assertEqual(payload["eventCodes"][0]["eventCodeType"], "GOV_ASSIGNED_IDENTIFIER")

    def test_event_code_subclass_used_for_items(self):
        """The override must use the local subclass so each item has
        ``generate_for_graphql_mutation``; otherwise it would fall back to
        pyhelix's bare model and the list comprehension would AttributeError."""
        country = CountryFactory.create()
        row = self._event_row(
            event_codes=[
                {
                    "uuid": "44444444-4444-4444-4444-444444444444",
                    "country_id": country.id,
                    "event_code": "ACLED-1",
                    "event_code_type": "ACLED_ID",
                }
            ]
        )
        event = HulkEventImport(**row)
        self.assertIsInstance(event.event_codes[0], HulkEventImportEventCode)

    def test_end_date_before_start_date_rejected(self):
        """A row whose ``end_date`` precedes ``start_date`` must be rejected —
        mirroring the figure/event serializer start<=end constraint."""
        row = self._event_row(
            start_date="2024-01-31",
            end_date="2024-01-01",
        )
        with self.assertRaises(ValidationError) as cm:
            HulkEventImport(**row)
        self.assertIn("The start date must be earlier than end date.", str(cm.exception))

    def test_end_date_equal_start_date_allowed(self):
        """A single-day event (``start_date == end_date``) stays valid."""
        row = self._event_row(
            start_date="2024-01-01",
            end_date="2024-01-01",
        )
        HulkEventImport(**row)

    def test_start_date_beyond_10_years_rejected(self):
        """``start_date`` more than 10 years in the future must be rejected."""
        far_future = datetime.date.today().replace(year=datetime.date.today().year + 11)
        row = self._event_row(
            start_date=far_future.isoformat(),
            end_date=far_future.isoformat(),
        )
        with self.assertRaises(ValidationError) as cm:
            HulkEventImport(**row)
        self.assertIn("start_date: This date cannot be more than 10 years in the future.", str(cm.exception))

    def test_end_date_beyond_10_years_rejected(self):
        """``end_date`` more than 10 years in the future must be rejected."""
        far_future = datetime.date.today().replace(year=datetime.date.today().year + 11)
        row = self._event_row(
            start_date="2024-01-01",
            end_date=far_future.isoformat(),
        )
        with self.assertRaises(ValidationError) as cm:
            HulkEventImport(**row)
        self.assertIn("end_date: This date cannot be more than 10 years in the future.", str(cm.exception))

    def test_dates_within_10_years_allowed(self):
        """A future date within the 10-year window stays valid."""
        near_future = datetime.date.today().replace(year=datetime.date.today().year + 5)
        row = self._event_row(
            start_date=near_future.isoformat(),
            end_date=near_future.isoformat(),
        )
        HulkEventImport(**row)

    def test_very_old_dates_allowed(self):
        """Very old dates (e.g. 1900) are intentional and must still import."""
        row = self._event_row(
            start_date="1900-01-01",
            end_date="1900-12-31",
        )
        HulkEventImport(**row)


class TestHulkEnumValidationFieldNames(HelixGraphQLTestCase):
    """An invalid enum value must be reported against the field actually at
    fault — not the hardcoded ``event_type`` label the shared parser used to
    emit regardless of which field was wrong."""

    def _event_row(self, **overrides) -> dict:
        country = CountryFactory.create()
        violence_sub_type = ViolenceSubTypeFactory.create()
        row = {
            "uuid": "11111111-1111-1111-1111-111111111111",
            "event_name": "Test event",
            "event_cause": "CONFLICT",
            "violence_sub_type_id": violence_sub_type.id,
            "disaster_sub_type_id": None,
            "other_sub_type_id": None,
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": "narrative",
            "countries_id": [country.id],
            "event_codes": [],
        }
        row.update(overrides)
        return row

    def test_invalid_event_cause_reports_event_cause(self):
        row = self._event_row(event_cause="NOT_A_CAUSE")
        with self.assertRaises(ValidationError) as cm:
            HulkEventImport(**row)
        self.assertIn("Invalid event_cause 'NOT_A_CAUSE'", str(cm.exception))

    def test_invalid_start_date_accuracy_reports_start_date_accuracy(self):
        row = self._event_row(start_date_accuracy="BAD_ACCURACY")
        with self.assertRaises(ValidationError) as cm:
            HulkEventImport(**row)
        message = str(cm.exception)
        self.assertIn("Invalid start_date_accuracy 'BAD_ACCURACY'", message)
        self.assertNotIn("Invalid event_type", message)

    def test_invalid_end_date_accuracy_reports_end_date_accuracy(self):
        row = self._event_row(end_date_accuracy="BAD_ACCURACY")
        with self.assertRaises(ValidationError) as cm:
            HulkEventImport(**row)
        self.assertIn("Invalid end_date_accuracy 'BAD_ACCURACY'", str(cm.exception))

    def test_invalid_nested_event_code_type_reports_event_code_type(self):
        """The nested ``event_codes[].event_code_type`` list model must also
        report its real field name rather than ``event_type``."""
        country = CountryFactory.create()
        row = self._event_row(
            event_codes=[
                {
                    "uuid": "22222222-2222-2222-2222-222222222222",
                    "country_id": country.id,
                    "event_code": "GLD-001",
                    "event_code_type": "INVALID_CODE_TYPE",
                }
            ]
        )
        with self.assertRaises(ValidationError) as cm:
            HulkEventImport(**row)
        message = str(cm.exception)
        self.assertIn("Invalid event_code_type 'INVALID_CODE_TYPE'", message)
        self.assertNotIn("Invalid event_type", message)


class TestHulkEntryImportPublishDate(HelixGraphQLTestCase):
    """``publish_date`` must not be more than 10 years in the future.

    Validation lives on the pyhelix parent model, so we exercise it directly to
    avoid the DB-backed attachment/source-preview lookups on the app subclass."""

    def _entry_row(self, **overrides) -> dict:
        row = {
            "uuid": "55555555-5555-5555-5555-555555555555",
            "hulk_import_type": "DOCUMENT",
            "attachment_uuid": "66666666-6666-6666-6666-666666666666",
            "entry_title": "Test entry",
            "publish_date": "2024-01-01",
            "is_confidential": False,
            "publishers_id": [1],
        }
        row.update(overrides)
        return row

    def test_publish_date_beyond_10_years_rejected(self):
        far_future = datetime.date.today().replace(year=datetime.date.today().year + 11)
        row = self._entry_row(publish_date=far_future.isoformat())
        with self.assertRaises(ValidationError) as cm:
            pyhelix_models.HulkEntryImport(**row)
        self.assertIn("publish_date: This date cannot be more than 10 years in the future.", str(cm.exception))

    def test_publish_date_within_10_years_allowed(self):
        near_future = datetime.date.today().replace(year=datetime.date.today().year + 5)
        row = self._entry_row(publish_date=near_future.isoformat())
        pyhelix_models.HulkEntryImport(**row)

    def test_publish_date_very_old_allowed(self):
        row = self._entry_row(publish_date="1900-01-01")
        pyhelix_models.HulkEntryImport(**row)


class TestHulkFigureImportDates(HelixGraphQLTestCase):
    """Figure ``start_date``/``end_date`` must not be more than 10 years in the
    future — mirroring ``FigureSerializer._validate_dates``.

    The check lives on the pyhelix parent (``parse_dates``) and bounds the
    resolved ``_start_date``/``_end_date``, so it covers both the flow dates
    (``start_date``/``end_date``) and the stock mapping
    (``stock_date`` -> start, ``stock_reporting_date`` -> end). We exercise the
    parent model directly to avoid the DB-backed entry/event/sub-type lookups on
    the app subclass, stubbing the sub-type existence check the ``figure_cause``
    validator performs."""

    def setUp(self) -> None:
        super().setUp()
        # parse_figure_cause only calls ``<manager>.validate_id_exists(id)``; a
        # no-op stub is enough to reach the date validation under test.
        stub_manager = types.SimpleNamespace(validate_id_exists=lambda _id: None)
        self.stub_client = types.SimpleNamespace(
            violence_sub_type_manager=stub_manager,
            disaster_sub_type_manager=stub_manager,
            other_sub_type_manager=stub_manager,
        )

    def _location(self, **overrides) -> dict:
        loc = {
            "uuid": "77777777-7777-7777-7777-777777777777",
            "display_name": "Kathmandu",
            "country_name": "Nepal",
            "country_code": "NP",
            "identifier": "ORIGIN",
            "accuracy": "ADM0",
            "geocoder": "GEONAME",
            "latitude": 27.7,
            "longitude": 85.3,
        }
        loc.update(overrides)
        return loc

    def _flow_row(self, **overrides) -> dict:
        row = {
            "uuid": "88888888-8888-8888-8888-888888888888",
            "entry_id": 1,
            "event_id": 1,
            "figure_cause": "CONFLICT",
            "violence_sub_type_id": 1,
            "category": "NEW_DISPLACEMENT",  # flow
            "term": "DISPLACED",
            "quantifier": "EXACT",
            "unit": "PERSON",
            "figure_role": "RECOMMENDED",
            "country_id": 1,
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "reported_figure": 100,
            "is_housing_destruction": False,
            "displacement_occurred": "BEFORE",
            "is_disaggregated": False,
            "analysis_text": "analysis",
            "source_excerpt_text": "excerpt",
            "include_idu": False,
            "idu_text": "",
            "locations": [self._location()],
            "sources_id": [1],
        }
        row.update(overrides)
        return row

    def _stock_row(self, **overrides) -> dict:
        # Stock figures clear the flow dates and set the stock dates instead.
        row = self._flow_row(
            category="IDPS",  # stock
            start_date=None,
            start_date_accuracy=None,
            end_date=None,
            end_date_accuracy=None,
            stock_date="2024-01-05",
            stock_date_accuracy="DAY",
            stock_reporting_date="2024-01-31",
        )
        row.update(overrides)
        return row

    @staticmethod
    def _far_future() -> str:
        today = datetime.date.today()
        return today.replace(year=today.year + 11).isoformat()

    @staticmethod
    def _near_future() -> str:
        today = datetime.date.today()
        return today.replace(year=today.year + 5).isoformat()

    # -- flow dates ----------------------------------------------------------

    def test_flow_start_date_beyond_10_years_rejected(self):
        row = self._flow_row(start_date=self._far_future(), end_date=self._far_future())
        with self.assertRaises(ValidationError) as cm, helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)
        self.assertIn("start_date: This date cannot be more than 10 years in the future.", str(cm.exception))

    def test_flow_end_date_beyond_10_years_rejected(self):
        row = self._flow_row(end_date=self._far_future())
        with self.assertRaises(ValidationError) as cm, helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)
        self.assertIn("end_date: This date cannot be more than 10 years in the future.", str(cm.exception))

    def test_flow_dates_within_10_years_allowed(self):
        row = self._flow_row(start_date=self._near_future(), end_date=self._near_future())
        with helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)

    def test_flow_very_old_dates_allowed(self):
        row = self._flow_row(start_date="1900-01-01", end_date="1900-12-31")
        with helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)

    def test_flow_end_date_before_start_date_rejected(self):
        """A flow figure whose ``end_date`` precedes ``start_date`` is rejected,
        naming the flow input fields."""
        row = self._flow_row(start_date="2024-01-31", end_date="2024-01-01")
        with self.assertRaises(ValidationError) as cm, helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)
        self.assertIn("The start_date must be earlier than end_date.", str(cm.exception))

    def test_flow_end_date_equal_start_date_allowed(self):
        """A single-day flow figure (``start_date == end_date``) stays valid."""
        row = self._flow_row(start_date="2024-01-01", end_date="2024-01-01")
        with helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)

    # -- stock dates (mapped to start/end) -----------------------------------

    def test_stock_date_beyond_10_years_rejected(self):
        """``stock_date`` maps to ``start_date``; a far-future value is rejected
        against the start bound, named after the stock input field."""
        row = self._stock_row(stock_date=self._far_future(), stock_reporting_date=self._far_future())
        with self.assertRaises(ValidationError) as cm, helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)
        message = str(cm.exception)
        self.assertIn("stock_date: This date cannot be more than 10 years in the future.", message)
        self.assertNotIn("start_date", message)

    def test_stock_reporting_date_beyond_10_years_rejected(self):
        """``stock_reporting_date`` maps to ``end_date``; a far-future value is
        rejected against the end bound, named after the stock input field."""
        row = self._stock_row(stock_reporting_date=self._far_future())
        with self.assertRaises(ValidationError) as cm, helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)
        message = str(cm.exception)
        self.assertIn("stock_reporting_date: This date cannot be more than 10 years in the future.", message)
        self.assertNotIn("end_date", message)

    def test_stock_reporting_date_before_stock_date_rejected(self):
        """A stock figure whose ``stock_reporting_date`` precedes ``stock_date``
        is rejected, naming the stock input fields rather than the internal
        start/end mapping."""
        row = self._stock_row(stock_date="2024-01-31", stock_reporting_date="2024-01-05")
        with self.assertRaises(ValidationError) as cm, helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)
        message = str(cm.exception)
        self.assertIn("The stock_date must be earlier than stock_reporting_date.", message)
        self.assertNotIn("start_date", message)
        self.assertNotIn("end_date", message)

    def test_stock_dates_within_10_years_allowed(self):
        row = self._stock_row(stock_date=self._near_future(), stock_reporting_date=self._near_future())
        with helix_client_context(self.stub_client):
            pyhelix_models.HulkFigureImport(**row)
