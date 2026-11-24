import csv
import datetime
import json
import os
import typing
from collections import Counter

from django.core.management.base import CommandError
from django.db import connection, models
from django.db.models import Case, F, When

from apps.contrib.management.base.snapshot import no_log
from apps.crisis.models import Crisis
from apps.gidd.models import GiddFigure
from apps.gidd.views import DISAGGREGATION_EXPORT_VALUES
from apps.organization.models import OrganizationKind, SourceType

KEY = "key"
SOURCES_TYPE = "sources_type"
SOURCES_SUB_TYPE = "sources_sub_type"
SNAPSHOT_FILE = "gidd_figures.csv"
PROGRESS_EVERY = 50_000


def _has_sub_type_column() -> bool:
    """True once gidd 0047 has added GiddFigure.sources_sub_type."""
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, GiddFigure._meta.db_table)
    return any(column.name == SOURCES_SUB_TYPE for column in columns)


def _published_columns(before=False) -> typing.List[str]:
    columns: typing.List[str] = [column for column in DISAGGREGATION_EXPORT_VALUES if column != SOURCES_SUB_TYPE]
    # Before gidd 0047 the table has no sources_sub_type column.
    if not before:
        columns.append(SOURCES_SUB_TYPE)
    return columns


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return json.dumps(list(value), ensure_ascii=False, default=str)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value)


def take_snapshot(path, before=False, log=no_log) -> int:
    """Write every GiddFigure's published columns to a CSV keyed by "<figure_raw_id>:<year>".

    before: the database is not migrated yet (gidd 0047), so sources_sub_type is left out.
    log(kind, message): kind is "step", "progress" or "done".
    """
    # NOTE: each snapshot only works on the database state it is meant for (see the command).
    if before and _has_sub_type_column():
        raise CommandError(
            "gidd 0047 has already run (sources_sub_type exists): the before snapshot must be taken before migrate."
        )
    if not before and not _has_sub_type_column():
        raise CommandError("gidd 0047 has not run yet (no sources_sub_type): use --before, or run migrate first.")
    columns = _published_columns(before)
    log(
        "step",
        f"Writing {os.path.basename(path)}: one row per published GIDD figure and year "
        f"(GiddFigure, what the GIDD downloads show; {len(columns)} published columns)",
    )
    seen: typing.Counter[str] = Counter()
    # Every row, not only those with locations: a row the exports drop must not hide a change.
    qs = (
        GiddFigure.objects.annotate(
            # Same as the disaggregated exports (apps/gidd/views.py).
            event_main_trigger=Case(
                When(gidd_event__cause=Crisis.CRISIS_TYPE.CONFLICT, then=F("gidd_event__violence__name")),
                When(gidd_event__cause=Crisis.CRISIS_TYPE.DISASTER, then=F("gidd_event__disaster_sub_type__name")),
                When(gidd_event__cause=Crisis.CRISIS_TYPE.OTHER, then=F("gidd_event__other_sub_type__name")),
                output_field=models.CharField(),
            ),
        )
        .order_by("figure_raw_id", "year", "id")
        .values(*columns)
    )
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([KEY, *columns])
        for row in qs.iterator(chunk_size=2000):
            key = f"{row['figure_raw_id']}:{row['year']}"
            seen[key] += 1
            # A figure published twice in one year keeps a stable key by its position.
            if seen[key] > 1:
                key = f"{key}#{seen[key]}"
            writer.writerow([key, *[_cell(row[column]) for column in columns]])
            count += 1
            if count % PROGRESS_EVERY == 0:
                log("progress", f"{count} GIDD figures written...")
    log("done", f"{count} GIDD figures written to {path}")
    return count


def _read(path) -> typing.Tuple[typing.List[str], typing.Dict[str, typing.Dict[str, str]]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = [column for column in reader.fieldnames or [] if column != KEY]
        return columns, {row[KEY]: row for row in reader}


def check_source_wording(path) -> typing.List[str]:
    """Problems with the published source wording in a snapshot; empty when it is correct.

    Every sources_type value must be a source type name, every sources_sub_type value a subtype name
    (an organization kind with a source type), and each row's lists must line up with its sources.
    """
    columns, rows = _read(path)
    if SOURCES_SUB_TYPE not in columns:
        return [f"column {SOURCES_SUB_TYPE} is missing (added in E7 PR 2)"]

    type_names = set(SourceType.objects.values_list("name", flat=True))
    subtype_names = set(OrganizationKind.objects.filter(source_type__isnull=False).values_list("name", flat=True))
    bad_types: typing.Counter[str] = Counter()
    bad_subtypes: typing.Counter[str] = Counter()
    misaligned = []
    for key, row in rows.items():
        sources = json.loads(row["sources"] or "[]")
        types = json.loads(row[SOURCES_TYPE] or "[]")
        subtypes = json.loads(row[SOURCES_SUB_TYPE] or "[]")
        if not len(sources) == len(types) == len(subtypes):
            misaligned.append(key)
        bad_types.update(value for value in types if value not in type_names)
        bad_subtypes.update(value for value in subtypes if value not in subtype_names)

    problems = []
    if bad_types:
        problems.append(
            "sources_type values that are not source type names: "
            + ", ".join(f"{name!r} ({n})" for name, n in bad_types.most_common())
        )
    if bad_subtypes:
        problems.append(
            "sources_sub_type values that are not subtype names: "
            + ", ".join(f"{name!r} ({n})" for name, n in bad_subtypes.most_common())
        )
    if misaligned:
        problems.append(
            f"{len(misaligned)} rows where sources, sources_type and sources_sub_type differ in length "
            f"(first 20: {', '.join(misaligned[:20])})"
        )
    return problems
