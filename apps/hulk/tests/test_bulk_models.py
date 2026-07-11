"""
Tests for the ``apps.hulk.bulk.models`` pydantic models — the layer that
converts JSONL input rows into the dict shape sent to helix GraphQL mutations
via ``generate_for_graphql_mutation``.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError

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
