"""
Regenerate the canonical hulk-bulk test fixtures under
``artifacts/fixtures/hulk-bulk/``.

Run manually after editing ``ROWS`` below::

    docker compose -p helix-server exec -T server python -m apps.hulk.tests._build_fixtures

What this writes:

* ``raw/<resource>.xlsx`` — the source-of-truth for each of the five resource
  types. Complex cell values (lists / dicts) are JSON-encoded strings so the
  files stay editable in Excel.
* ``expected/jsonl/<resource>.jsonl`` — the deterministic JSONL the test
  fixture loader produces from the xlsx. These are what gets uploaded to
  ``HulkBulkImport.import_<resource>``.
* ``expected/success/<resource>.jsonl`` — one row per UUID that the handler
  is expected to count as a success, with ``message`` set to the expected
  marker. ``id`` is stripped because factory-created Django PKs aren't
  deterministic across test runs.
* ``expected/failure/<resource>.jsonl`` — one row per UUID expected to fail,
  with ``error_key`` set to either ``pre-errors`` (pydantic validation,
  resolved before mutation) or ``post-errors`` (helix returned an error
  on the mutation).

This file is a developer tool, not a test. It is excluded from the
``name-tests-test`` pre-commit hook.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from openpyxl import Workbook

# --- Determinism -------------------------------------------------------------
NS = uuid.UUID("00000000-0000-0000-0000-000000000999")


def _u(label: str) -> str:
    return str(uuid.uuid5(NS, label))


ATTACHMENT_UUIDS = {
    "ok_entry": _u("attachment:ok_entry"),
    "ok_document": _u("attachment:ok_document"),
}
SOURCE_PREVIEW_UUIDS = {
    "ok": _u("source_preview:ok"),
}
ENTRY_UUIDS = {
    "doc": _u("entry:doc"),
    "url": _u("entry:url"),
    "doc2": _u("entry:doc2"),
    "bad_no_ref": _u("entry:bad_no_ref"),
}
EVENT_UUIDS = {
    "conflict": _u("event:conflict"),
    "disaster": _u("event:disaster"),
    "other": _u("event:other"),
    "blank_narrative": _u("event:blank_narrative"),
}
FIGURE_UUIDS = {
    "person_null_hh": _u("figure:person_null_hh"),
    "household": _u("figure:household"),
    "stock": _u("figure:stock"),
    "bad_country": _u("figure:bad_country"),
    "missing_event": _u("figure:missing_event"),
}

DUMMY_FILE_URL = "https://example.invalid/test.pdf"

# Stable per-location UUIDs so xlsx + JSONL stay bit-identical across regens.
LOCATION_UUIDS = {
    "np_origin": _u("location:np_origin"),
    "np_origin_b": _u("location:np_origin_b"),
    "np_origin_c": _u("location:np_origin_c"),
    "cn_origin": _u("location:cn_origin"),
    "np_origin_d": _u("location:np_origin_d"),
}

# Placeholders that ``FixtureContext`` will substitute at test time. Stored in
# the xlsx as literal strings so we don't bake real PKs into the fixture.
PH_COUNTRY = "{{COUNTRY_ID}}"
PH_PUBLISHER = "{{PUBLISHER_ID}}"
PH_SOURCE = "{{SOURCE_ID}}"
PH_VIOLENCE = "{{VIOLENCE_SUB_TYPE_ID}}"
PH_DISASTER = "{{DISASTER_SUB_TYPE_ID}}"
PH_OTHER = "{{OTHER_SUB_TYPE_ID}}"


def _location(uuid_key: str, country_code: str = "NP") -> dict:
    return {
        "uuid": LOCATION_UUIDS[uuid_key],
        "bounding_box": None,
        "display_name": "Test Location",
        "country_name": "Nepal" if country_code == "NP" else "China",
        "country_code": country_code,
        "identifier": "ORIGIN",
        "accuracy": "ADM0",
        "geocoder": "CUSTOM_SOURCE",
        "latitude": 28.0,
        "longitude": 84.0,
    }


# --- Row definitions ---------------------------------------------------------
ROWS = {
    "attachments": [
        {"uuid": ATTACHMENT_UUIDS["ok_entry"], "attachment_for": "ENTRY", "file_url": DUMMY_FILE_URL},
        {"uuid": ATTACHMENT_UUIDS["ok_document"], "attachment_for": "ENTRY", "file_url": DUMMY_FILE_URL},
    ],
    "source_previews": [
        {"uuid": SOURCE_PREVIEW_UUIDS["ok"], "file_url": "https://example.com/test-page"},
    ],
    "entries": [
        {
            "uuid": ENTRY_UUIDS["doc"],
            "hulk_import_type": "DOCUMENT",
            "attachment_uuid": ATTACHMENT_UUIDS["ok_entry"],
            "source_preview_uuid": None,
            "url": None,
            "entry_title": "Doc entry",
            "publish_date": "2024-01-15",
            "is_confidential": False,
            "publishers_id": [PH_PUBLISHER],
        },
        {
            "uuid": ENTRY_UUIDS["url"],
            "hulk_import_type": "URL",
            "attachment_uuid": None,
            "source_preview_uuid": SOURCE_PREVIEW_UUIDS["ok"],
            "url": "https://example.com/test-page",
            "entry_title": "URL entry",
            "publish_date": "2024-01-15",
            "is_confidential": False,
            "publishers_id": [PH_PUBLISHER],
        },
        {
            "uuid": ENTRY_UUIDS["doc2"],
            "hulk_import_type": "DOCUMENT",
            "attachment_uuid": ATTACHMENT_UUIDS["ok_document"],
            "source_preview_uuid": None,
            "url": None,
            "entry_title": "Doc entry 2",
            "publish_date": "2024-01-15",
            "is_confidential": False,
            "publishers_id": [PH_PUBLISHER],
        },
        {
            "uuid": ENTRY_UUIDS["bad_no_ref"],
            "hulk_import_type": "DOCUMENT",
            "attachment_uuid": None,
            "source_preview_uuid": None,
            "url": None,
            "entry_title": "Bad entry — no ref",
            "publish_date": "2024-01-15",
            "is_confidential": False,
            "publishers_id": [PH_PUBLISHER],
        },
    ],
    "events": [
        {
            "uuid": EVENT_UUIDS["conflict"],
            "event_name": "Conflict event",
            "event_cause": "CONFLICT",
            "violence_sub_type_id": PH_VIOLENCE,
            "disaster_sub_type_id": None,
            "other_sub_type_id": None,
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": "Conflict narrative",
            "countries_id": [PH_COUNTRY],
            "event_codes": [],
        },
        {
            "uuid": EVENT_UUIDS["disaster"],
            "event_name": "Disaster event",
            "event_cause": "DISASTER",
            "violence_sub_type_id": None,
            "disaster_sub_type_id": PH_DISASTER,
            "other_sub_type_id": None,
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": "Disaster narrative",
            "countries_id": [PH_COUNTRY],
            "event_codes": [],
        },
        {
            "uuid": EVENT_UUIDS["other"],
            "event_name": "Other event",
            "event_cause": "OTHER",
            "violence_sub_type_id": None,
            "disaster_sub_type_id": None,
            "other_sub_type_id": PH_OTHER,
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": "Other narrative",
            "countries_id": [PH_COUNTRY],
            "event_codes": [],
        },
        {
            "uuid": EVENT_UUIDS["blank_narrative"],
            "event_name": "Conflict event blank narrative",
            "event_cause": "CONFLICT",
            "violence_sub_type_id": PH_VIOLENCE,
            "disaster_sub_type_id": None,
            "other_sub_type_id": None,
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": "",  # rejected by helix serializer → post-error
            "countries_id": [PH_COUNTRY],
            "event_codes": [],
        },
    ],
}


def _figure_base() -> dict:
    return {
        "entry_uuid": ENTRY_UUIDS["doc"],
        "event_uuid": EVENT_UUIDS["disaster"],
        "figure_cause": "DISASTER",
        "violence_sub_type_id": None,
        "disaster_sub_type_id": PH_DISASTER,
        "other_sub_type_id": None,
        "category": "NEW_DISPLACEMENT",
        "term": "DISPLACED",
        "quantifier": "EXACT",
        "figure_role": "RECOMMENDED",
        "country_id": PH_COUNTRY,
        "displacement_occurred": "UNKNOWN",
        "is_housing_destruction": False,
        "is_disaggregated": False,
        "include_idu": False,
        "idu_text": "-",
        "analysis_text": "-",
        "source_excerpt_text": "-",
        "tags_id": [],
        "sources_id": [PH_SOURCE],
        # Flow defaults — stock fixture clears these.
        "start_date": "2024-01-05",
        "start_date_accuracy": "DAY",
        "end_date": "2024-01-10",
        "end_date_accuracy": "DAY",
        "stock_date": None,
        "stock_date_accuracy": None,
        "stock_reporting_date": None,
    }


ROWS["figures"] = [
    # 1. PERSON unit, household_size=None — verifies None passes through.
    {
        **_figure_base(),
        "uuid": FIGURE_UUIDS["person_null_hh"],
        "unit": "PERSON",
        "reported_figure": 100,
        "household_size": None,
        "locations": [_location("np_origin")],
    },
    # 2. HOUSEHOLD unit, explicit household_size.
    {
        **_figure_base(),
        "uuid": FIGURE_UUIDS["household"],
        "unit": "HOUSEHOLD",
        "reported_figure": 25,
        "household_size": 4.5,
        "locations": [_location("np_origin_b")],
    },
    # 3. Stock figure — clears flow dates, sets stock dates and stock category.
    {
        **{
            k: v
            for k, v in _figure_base().items()
            if k not in {"start_date", "end_date", "start_date_accuracy", "end_date_accuracy"}
        },
        "uuid": FIGURE_UUIDS["stock"],
        "category": "IDPS",
        "unit": "PERSON",
        "reported_figure": 200,
        "household_size": None,
        "start_date": None,
        "start_date_accuracy": None,
        "end_date": None,
        "end_date_accuracy": None,
        "stock_date": "2024-01-05",
        "stock_date_accuracy": "DAY",
        "stock_reporting_date": "2024-01-10",
        "locations": [_location("np_origin_c")],
    },
    # 4. Post-error: location country_code mismatch (figure says NP, location says CN).
    {
        **_figure_base(),
        "uuid": FIGURE_UUIDS["bad_country"],
        "unit": "PERSON",
        "reported_figure": 50,
        "household_size": None,
        "locations": [_location("cn_origin", country_code="CN")],
    },
    # 5. Pre-error: references an event_uuid not present in events.jsonl.
    {
        **_figure_base(),
        "uuid": FIGURE_UUIDS["missing_event"],
        "event_uuid": _u("event:never_present"),
        "unit": "PERSON",
        "reported_figure": 10,
        "household_size": None,
        "locations": [_location("np_origin_d")],
    },
]


# --- Expected outcomes per fixture row ---------------------------------------
# success: row gets created end-to-end; failure: row goes to failure_<resource>
# with the named error key.
EXPECTED_OUTCOMES = {
    "attachments": {
        ATTACHMENT_UUIDS["ok_entry"]: {"outcome": "success", "message": "Created"},
        ATTACHMENT_UUIDS["ok_document"]: {"outcome": "success", "message": "Created"},
    },
    "source_previews": {
        SOURCE_PREVIEW_UUIDS["ok"]: {"outcome": "success", "message": "Created"},
    },
    "entries": {
        ENTRY_UUIDS["doc"]: {"outcome": "success", "message": "Created"},
        ENTRY_UUIDS["url"]: {"outcome": "success", "message": "Created"},
        ENTRY_UUIDS["doc2"]: {"outcome": "success", "message": "Created"},
        # Missing both attachment_uuid (DOCUMENT type) → pydantic ValidationError
        # from HulkEntryImport.parse_document.
        ENTRY_UUIDS["bad_no_ref"]: {
            "outcome": "failure",
            "error_key": "pre-errors",
            "error_match": "attachment_uuid is required",
        },
    },
    "events": {
        EVENT_UUIDS["conflict"]: {"outcome": "success", "message": "Created"},
        EVENT_UUIDS["disaster"]: {"outcome": "success", "message": "Created"},
        EVENT_UUIDS["other"]: {"outcome": "success", "message": "Created"},
        # Blank event_narrative → helix serializer rejects → GraphQL post-error.
        EVENT_UUIDS["blank_narrative"]: {
            "outcome": "failure",
            "error_key": "post-errors",
            "error_match": "This field may not be blank",
        },
    },
    "figures": {
        FIGURE_UUIDS["person_null_hh"]: {"outcome": "success", "message": "Created"},
        FIGURE_UUIDS["household"]: {"outcome": "success", "message": "Created"},
        FIGURE_UUIDS["stock"]: {"outcome": "success", "message": "Created"},
        # Location iso2 mismatch — helix serializer post-error.
        FIGURE_UUIDS["bad_country"]: {
            "outcome": "failure",
            "error_key": "post-errors",
            "error_match": "Location should be inside the selected figure's country",
        },
        # Missing event UUID — pydantic ValidationError from HulkFigureImport.parse_event.
        FIGURE_UUIDS["missing_event"]: {
            "outcome": "failure",
            "error_key": "pre-errors",
            "error_match": "Unknown event",
        },
    },
}


# --- Writers -----------------------------------------------------------------
# openpyxl drops empty strings on read (returns None). Use a sentinel to
# distinguish a deliberately-empty string ("") from a missing cell (None).
EMPTY_STRING_SENTINEL = "<EMPTY_STRING>"


def _cell_value(value):
    """openpyxl-friendly cell value. Lists/dicts/None go through json.dumps."""
    if value == "":
        return EMPTY_STRING_SENTINEL
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value)


def write_xlsx(path: Path, rows: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "rows"
    if not rows:
        wb.save(path)
        return
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([_cell_value(row.get(h)) for h in headers])
    wb.save(path)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    base = repo_root / "artifacts" / "fixtures" / "hulk-bulk"
    raw = base / "raw"
    expected_jsonl = base / "expected" / "jsonl"
    expected_success = base / "expected" / "success"
    expected_failure = base / "expected" / "failure"
    for d in (raw, expected_jsonl, expected_success, expected_failure):
        d.mkdir(parents=True, exist_ok=True)

    for resource, rows in ROWS.items():
        write_xlsx(raw / f"{resource}.xlsx", rows)
        # Expected JSONL == the loader's output for these rows. Same data,
        # just one JSON object per line so byte-comparison is meaningful.
        write_jsonl(expected_jsonl / f"{resource}.jsonl", rows)

        success_rows = []
        failure_rows = []
        for row in rows:
            outcome = EXPECTED_OUTCOMES[resource][row["uuid"]]
            if outcome["outcome"] == "success":
                success_rows.append({"uuid": row["uuid"], "message": outcome["message"]})
            else:
                failure_rows.append(
                    {
                        "uuid": row["uuid"],
                        "error_key": outcome["error_key"],
                        "error_match": outcome["error_match"],
                    }
                )
        write_jsonl(expected_success / f"{resource}.jsonl", success_rows)
        write_jsonl(expected_failure / f"{resource}.jsonl", failure_rows)

    print(f"Wrote fixtures under {base}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    # Allow running outside Django since we only touch openpyxl + stdlib.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "helix.settings")
    sys.exit(main())
