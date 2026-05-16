"""
Snapshot the helix-side rows a ``HulkBulkImport`` created.

Used as a regression-detection golden for the hulk handler: re-run the
fixture, dump the resulting entity rows, and bit-compare against
``artifacts/fixtures/hulk-bulk/expected/db-state.json``. Any change to the
handler / serializer / pyhelix model that perturbs what gets written
will surface as a snapshot diff.

Design choices:

* We snapshot the *underlying entity* (Attachment / SourcePreview / Entry /
  Event / Figure) joined via the ``HulkXxx`` relation tables — that way the
  snapshot is naturally scoped to a single bulk import and keyed by the
  ``HulkXxx.uuid`` the user originally uploaded.
* Only stable scalar fields are included: enums emit ``.name``, dates emit
  ISO strings, FK columns resolve to a stable identifier on the referenced
  row (``Country.iso2``, ``Organization.name``, sub-type names) rather than
  the non-deterministic factory PK.
* Rows are emitted sorted by ``uuid`` for deterministic byte-comparison.
"""

from __future__ import annotations

import datetime
import typing

from apps.contrib.models import Attachment, SourcePreview
from apps.entry.models import Entry, Figure
from apps.event.models import Event
from apps.hulk.models import (
    HulkAttachment,
    HulkBulkImport,
    HulkEntry,
    HulkEvent,
    HulkFigure,
    HulkSourcePreview,
)


def _enum_name(value) -> typing.Optional[str]:
    if value is None:
        return None
    return getattr(value, "name", None) or str(value)


def _iso(value) -> typing.Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value)


def _country_iso2(country) -> typing.Optional[str]:
    return getattr(country, "iso2", None) if country else None


def _name(obj) -> typing.Optional[str]:
    return getattr(obj, "name", None) if obj else None


def _attachment_uuid_for_entity(entity_id: int) -> typing.Optional[str]:
    row = HulkAttachment.objects.filter(entity_id=entity_id).first()
    return str(row.uuid) if row else None


def _source_preview_uuid_for_entity(entity_id: int) -> typing.Optional[str]:
    row = HulkSourcePreview.objects.filter(entity_id=entity_id).first()
    return str(row.uuid) if row else None


def _entry_uuid_for_entity(entity_id: int) -> typing.Optional[str]:
    row = HulkEntry.objects.filter(entity_id=entity_id).first()
    return str(row.uuid) if row else None


def _event_uuid_for_entity(entity_id: int) -> typing.Optional[str]:
    row = HulkEvent.objects.filter(entity_id=entity_id).first()
    return str(row.uuid) if row else None


def _attachment_row(a: Attachment, *, uuid: str) -> dict:
    return {
        "uuid": uuid,
        "attachment_for": _enum_name(a.attachment_for),
        "mimetype": a.mimetype,
    }


def _source_preview_row(sp: SourcePreview, *, uuid: str) -> dict:
    return {
        "uuid": uuid,
        "url": sp.url,
        "status": _enum_name(sp.status),
    }


def _entry_row(e: Entry, *, uuid: str) -> dict:
    publishers = list(e.publishers.values_list("name", flat=True).order_by("name"))
    return {
        "uuid": uuid,
        "article_title": e.article_title,
        "publish_date": _iso(e.publish_date),
        "is_confidential": e.is_confidential,
        "document_uuid": _attachment_uuid_for_entity(e.document_id) if e.document_id else None,
        "preview_uuid": _source_preview_uuid_for_entity(e.preview_id) if e.preview_id else None,
        "publishers": publishers,
    }


def _event_row(ev: Event, *, uuid: str) -> dict:
    countries = sorted(
        [c for c in ev.countries.values_list("iso2", flat=True) if c],
    )
    return {
        "uuid": uuid,
        "name": ev.name,
        "event_type": _enum_name(ev.event_type),
        "start_date": _iso(ev.start_date),
        "start_date_accuracy": _enum_name(ev.start_date_accuracy),
        "end_date": _iso(ev.end_date),
        "end_date_accuracy": _enum_name(ev.end_date_accuracy),
        "event_narrative": ev.event_narrative,
        "violence_sub_type": _name(ev.violence_sub_type),
        "disaster_sub_type": _name(ev.disaster_sub_type),
        "other_sub_type": _name(ev.other_sub_type),
        "countries": countries,
    }


def _figure_row(f: Figure, *, uuid: str) -> dict:
    locations = [
        {
            "country_code": loc.country_code,
            "identifier": _enum_name(loc.identifier),
            "accuracy": _enum_name(loc.accuracy),
            "geocoder": _enum_name(loc.geocoder),
            "lat": loc.lat,
            "lon": loc.lon,
        }
        for loc in f.geo_locations.all().order_by("country_code", "identifier")
    ]
    return {
        "uuid": uuid,
        "figure_cause": _enum_name(f.figure_cause),
        "category": _enum_name(f.category),
        "term": _enum_name(f.term),
        "quantifier": _enum_name(f.quantifier),
        "unit": _enum_name(f.unit),
        "role": _enum_name(f.role),
        "reported": f.reported,
        "household_size": f.household_size,
        "is_housing_destruction": f.is_housing_destruction,
        "is_disaggregated": f.is_disaggregated,
        "include_idu": f.include_idu,
        "displacement_occurred": _enum_name(f.displacement_occurred),
        "calculation_logic": f.calculation_logic,
        "source_excerpt": f.source_excerpt,
        "excerpt_idu": f.excerpt_idu,
        "start_date": _iso(f.start_date),
        "start_date_accuracy": _enum_name(f.start_date_accuracy),
        "end_date": _iso(f.end_date),
        "end_date_accuracy": _enum_name(f.end_date_accuracy),
        "country": _country_iso2(f.country),
        "entry_uuid": _entry_uuid_for_entity(f.entry_id) if f.entry_id else None,
        "event_uuid": _event_uuid_for_entity(f.event_id) if f.event_id else None,
        "violence_sub_type": _name(f.violence_sub_type),
        "disaster_sub_type": _name(f.disaster_sub_type),
        "other_sub_type": _name(f.other_sub_type),
        "locations": locations,
    }


def dump_db_state(bulk_import: HulkBulkImport) -> dict:
    """
    Return a deterministic snapshot of the helix entity rows created by
    ``bulk_import``. Top-level keys are the five resource short names; values
    are lists of dicts sorted by ``uuid``.
    """

    def _sorted_rows(qs, row_fn):
        rows = []
        for rel in qs.select_related("entity"):
            if rel.entity is None:
                continue
            rows.append(row_fn(rel.entity, uuid=str(rel.uuid)))
        rows.sort(key=lambda r: r["uuid"])
        return rows

    return {
        "attachments": _sorted_rows(
            HulkAttachment.objects.filter(bulk_import=bulk_import),
            _attachment_row,
        ),
        "source_previews": _sorted_rows(
            HulkSourcePreview.objects.filter(bulk_import=bulk_import),
            _source_preview_row,
        ),
        "entries": _sorted_rows(
            HulkEntry.objects.filter(bulk_import=bulk_import),
            _entry_row,
        ),
        "events": _sorted_rows(
            HulkEvent.objects.filter(bulk_import=bulk_import),
            _event_row,
        ),
        "figures": _sorted_rows(
            HulkFigure.objects.filter(bulk_import=bulk_import),
            _figure_row,
        ),
    }
