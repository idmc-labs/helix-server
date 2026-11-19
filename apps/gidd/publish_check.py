"""A7.2.6: check that the published GIDD figures change only in source wording after A7.2.3.

The disaggregated Excel and GeoJSON downloads read GiddFigure (DISAGGREGATION_EXPORT_VALUES), which
the publish step (update_gidd_data / force_update_gidd_data) regenerates.

Outside production, on the same data:
1. publish, then `snapshot_gidd_figures before.csv`
2. deploy E7 PR 2 (A7.2.3 runs), publish, then `snapshot_gidd_figures after.csv`
3. `compare_gidd_figures before.csv after.csv <out_dir>` must PASS: the rows match, only `sources_type`
   changes, and `sources_sub_type` is the only new column.
In production, after the first release published after A7.2.3:
4. `snapshot_gidd_figures release.csv`, then `check_gidd_source_wording release.csv` must PASS.
"""

import csv
import datetime
import json
import os
import typing
from collections import Counter

from django.db import models
from django.db.models import Case, F, When

from apps.crisis.models import Crisis
from apps.gidd.models import GiddFigure
from apps.gidd.views import DISAGGREGATION_EXPORT_VALUES
from apps.organization.models import OrganizationKind, SourceType

KEY = "key"
SOURCES_TYPE = "sources_type"
SOURCES_SUB_TYPE = "sources_sub_type"
# The only published change A7.2.3 may cause: the type column carries the type name ...
ALLOWED_CHANGED_COLUMNS = {SOURCES_TYPE}
# ... and the subtype column is new (added in E7 PR 2).
ALLOWED_NEW_COLUMNS = {SOURCES_SUB_TYPE}


def _published_columns() -> typing.List[str]:
    columns: typing.List[str] = list(DISAGGREGATION_EXPORT_VALUES)
    field_names = {field.name for field in GiddFigure._meta.get_fields()}
    if SOURCES_SUB_TYPE in field_names and SOURCES_SUB_TYPE not in columns:
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


def take_snapshot(path) -> int:
    """Write every GiddFigure's published columns to a CSV keyed by "<figure_raw_id>:<year>"."""
    columns = _published_columns()
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
    return count


def _read(path) -> typing.Tuple[typing.List[str], typing.Dict[str, typing.Dict[str, str]]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = [column for column in reader.fieldnames or [] if column != KEY]
        return columns, {row[KEY]: row for row in reader}


def compare_snapshots(before_path, after_path, out_dir) -> typing.Tuple[bool, typing.List[str]]:
    """Write report.md and changed_cells.csv to out_dir; return (passed, failure reasons)."""
    os.makedirs(out_dir, exist_ok=True)
    before_columns, before = _read(before_path)
    after_columns, after = _read(after_path)

    removed_columns = sorted(set(before_columns) - set(after_columns))
    new_columns = sorted(set(after_columns) - set(before_columns))
    missing_rows = sorted(set(before) - set(after))
    added_rows = sorted(set(after) - set(before))
    common_columns = [column for column in before_columns if column in after_columns]

    changed_by_column: typing.Counter[str] = Counter()
    with open(os.path.join(out_dir, "changed_cells.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([KEY, "column", "before", "after"])
        for key in sorted(set(before) & set(after)):
            for column in common_columns:
                if before[key][column] != after[key][column]:
                    changed_by_column[column] += 1
                    writer.writerow([key, column, before[key][column], after[key][column]])

    failures = []
    if removed_columns:
        failures.append(f"columns removed: {', '.join(removed_columns)}")
    unexpected_new = sorted(set(new_columns) - ALLOWED_NEW_COLUMNS)
    if unexpected_new:
        failures.append(f"unexpected new columns: {', '.join(unexpected_new)}")
    missing_new = sorted(ALLOWED_NEW_COLUMNS - set(after_columns))
    if missing_new:
        failures.append(f"expected new columns missing: {', '.join(missing_new)}")
    if missing_rows:
        failures.append(f"{len(missing_rows)} rows missing after")
    if added_rows:
        failures.append(f"{len(added_rows)} rows added after")
    unexpected_changes = {column: n for column, n in changed_by_column.items() if column not in ALLOWED_CHANGED_COLUMNS}
    if unexpected_changes:
        failures.append(
            "unexpected changes in: " + ", ".join(f"{column} ({n})" for column, n in sorted(unexpected_changes.items()))
        )

    passed = not failures
    lines = [
        f"# GIDD published figures: before vs after (A7.2.6) — {'PASS' if passed else 'FAIL'}",
        "",
        f"- Rows: {len(before)} before, {len(after)} after",
        f"- Missing after: {len(missing_rows)}, added after: {len(added_rows)}",
        f"- New columns: {', '.join(new_columns) or '-'}; removed columns: {', '.join(removed_columns) or '-'}",
        "",
        "## Changed cells by column",
        "",
        "| Column | Cells changed | Allowed |",
        "|---|---|---|",
        *[
            f"| {column} | {n} | {'yes' if column in ALLOWED_CHANGED_COLUMNS else 'no'} |"
            for column, n in sorted(changed_by_column.items())
        ],
        "",
    ]
    if failures:
        lines += ["## Failures", "", *[f"- {failure}" for failure in failures], ""]
    if missing_rows or added_rows:
        lines += [
            f"Missing after (first 20): {', '.join(missing_rows[:20]) or '-'}",
            f"Added after (first 20): {', '.join(added_rows[:20]) or '-'}",
            "",
        ]
    lines.append("Details: changed_cells.csv")
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return passed, failures


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
