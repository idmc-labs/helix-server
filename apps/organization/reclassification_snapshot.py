"""Record each organization's kind and each figure's classification and IDU source wording.
Take one snapshot before the organization migrations (0013, 0014) and one after, and compare them by hand.

A snapshot is a directory with two CSV files.
After (take_snapshot):
- organizations.csv: organization_id, name, archived, kind_id, kind, source_type, level
- figures.csv: figure_id, classification, idu_source_wording
Before (take_before_snapshot), read with raw SQL from the database not yet migrated, where the kind
still has its reliability column:
- organizations.csv: the same columns, plus reliability
- figures.csv: figure_id, reliability, idu_source_wording (as the code before E7 wrote them)

Levels are numbers (1 = High, 3 = Low).

NOTE: each snapshot only works on the database state it is meant for, and refuses the other one:
- before needs the kind's reliability column, which organization 0014 drops. Once migrated, the old
  reliability is gone, so a before snapshot can no longer be taken: take it before running migrate.
- after reads the new source types; on a database not yet migrated the old kinds have none, so
  every level would be empty.
"""

import csv
import itertools
import os
import typing

from django.core.management.base import CommandError
from django.db import connection

from apps.contrib.management.base.snapshot import no_log
from apps.entry.models import Figure
from apps.entry.utils import format_source, join_with_and
from apps.organization.models import Organization, OrganizationKind, SourceType

ORGANIZATION_COLUMNS = ["organization_id", "name", "archived", "kind_id", "kind", "source_type", "level"]
FIGURE_COLUMNS = ["figure_id", "classification", "idu_source_wording"]
BEFORE_ORGANIZATION_COLUMNS = [*ORGANIZATION_COLUMNS, "reliability"]
BEFORE_FIGURE_COLUMNS = ["figure_id", "reliability", "idu_source_wording"]
ORGANIZATIONS_FILE = "organizations.csv"
FIGURES_FILE = "figures.csv"
ORGANIZATION_ROW = "organization (source)"
# Helix's own figures (entry_figure), not the published GIDD figures (snapshot_gidd_figures).
FIGURE_ROW = "Helix figure"
PROGRESS_EVERY = 100_000

# log(kind, message): kind is "step" (a new step starts), "progress" (rows written so far) or
# "done" (a file is written).
Log = typing.Callable[[str, str], None]


def _is_migrated() -> bool:
    """True once organization 0014 has dropped the kind's reliability column."""
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, OrganizationKind._meta.db_table)
    return not any(column.name == "reliability" for column in columns)


def _value(value):
    """The number behind an enum value, whichever form the query returned."""
    return getattr(value, "value", value)


def _write_csv(path, columns, rows, label: str, log: Log) -> int:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        count = 0
        for row in rows:
            writer.writerow(["" if value is None else value for value in row])
            count += 1
            if count % PROGRESS_EVERY == 0:
                log("progress", f"{count} {label} written...")
    log("done", f"{count} {label} written to {path}")
    return count


def _take(out_dir, files, log: Log) -> typing.Dict[str, int]:
    """files: (label, file name, what one row is, columns, rows) for each CSV."""
    os.makedirs(out_dir, exist_ok=True)
    counts = {}
    for label, file_name, row_is, columns, rows in files:
        log("step", f"Writing {file_name}: one row per {row_is} ({', '.join(columns)})")
        counts[label] = _write_csv(os.path.join(out_dir, file_name), columns, rows, label, log)
    return counts


def _organization_rows():
    qs = Organization.objects.order_by("id").values_list(
        "id",
        "name",
        "deleted_on",
        "organization_kind_id",
        "organization_kind__name",
        "organization_kind__source_type__name",
        "organization_kind__source_type__level",
    )
    for org_id, name, deleted_on, kind_id, kind, source_type, level in qs.iterator(chunk_size=2000):
        level = _value(level)
        yield [org_id, name, "yes" if deleted_on else "no", kind_id, kind, source_type, level]


def _figure_rows():
    classifications = dict(
        Figure.objects.annotate(**Figure.annotate_sources_classification()).values_list("id", "sources_classification")
    )
    # Sources in a fixed order, so the IDU wording does not depend on the database's row order.
    sources = (
        Figure.sources.through.objects.order_by("figure_id", "organization_id")
        .values_list(
            "figure_id",
            "organization__name",
            "organization__organization_kind__name",
            "organization__organization_kind__source_type__name",
        )
        .iterator(chunk_size=5000)
    )
    sources_by_figure = itertools.groupby(sources, key=lambda row: row[0])
    next_group = next(sources_by_figure, None)
    for figure_id in sorted(classifications):
        wording = ""
        if next_group is not None and next_group[0] == figure_id:
            wording = format_source(
                [
                    {"name": name, "organization_kind": kind, "source_type": source_type}
                    for _, name, kind, source_type in next_group[1]
                ]
            )
            next_group = next(sources_by_figure, None)
        yield [figure_id, classifications[figure_id], wording]


def take_snapshot(out_dir, log: Log = no_log) -> typing.Dict[str, int]:
    """The snapshot of the database after the organization migrations (0013, 0014)."""
    if not _is_migrated():
        raise CommandError(
            "The organization migrations (0013, 0014) have not run yet: take the before snapshot with --before, "
            "or run migrate first."
        )
    return _take(
        out_dir,
        [
            ("organizations", ORGANIZATIONS_FILE, ORGANIZATION_ROW, ORGANIZATION_COLUMNS, _organization_rows()),
            ("figures", FIGURES_FILE, FIGURE_ROW, FIGURE_COLUMNS, _figure_rows()),
        ],
        log,
    )


# Before: the database not yet migrated The models no longer have the kind's
# reliability, so these read it with raw SQL.

# OrganizationKind.reliability before E7 (0 = Low, 1 = Medium, 2 = High).
RELIABILITY_LABELS = {0: "Low", 1: "Medium", 2: "High"}


def _figure_reliability(reliabilities: typing.Sequence[int]) -> str:
    """A figure's reliability before E7: its sources' range, e.g. "Low to high"; "" with none."""
    if not reliabilities:
        return ""
    low, high = RELIABILITY_LABELS[min(reliabilities)], RELIABILITY_LABELS[max(reliabilities)]
    return low if low == high else f"{low} to {high.lower()}"


def _format_source_before(sources: typing.Sequence[typing.Tuple[str, typing.Optional[str]]]) -> str:
    """The IDU source wording before E7, from (name, kind name): copy of the old format_source."""
    old_phrases = (
        ("Local Authority", "local authorities"),
        ("Government", "national authorities"),
        ("Media", "media sources"),
    )
    kinds = {kind for _, kind in sources}
    labels = [phrase for kind, phrase in old_phrases if kind in kinds]
    collapsed = {kind for kind, _ in old_phrases}
    seen: typing.Set[str] = set()
    for name, kind in sources:
        if kind in collapsed or name is None or name in seen:
            continue
        seen.add(name)
        labels.append(name)
    return join_with_and(labels)


def _query(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        while True:
            rows = cursor.fetchmany(5000)
            if not rows:
                return
            yield from rows


def _organization_rows_before():
    sql = f"""
        SELECT org.id, org.name, org.deleted_on, org.organization_kind_id, kind.name, source_type.name,
               source_type.level, kind.reliability
        FROM {Organization._meta.db_table} org
        LEFT JOIN {OrganizationKind._meta.db_table} kind ON kind.id = org.organization_kind_id
        LEFT JOIN {SourceType._meta.db_table} source_type ON source_type.id = kind.source_type_id
        ORDER BY org.id
    """
    for org_id, name, deleted_on, kind_id, kind, source_type, level, reliability in _query(sql):
        archived = "yes" if deleted_on else "no"
        yield [org_id, name, archived, kind_id, kind, source_type, level, RELIABILITY_LABELS.get(reliability)]


def _figure_rows_before():
    figure_ids = [row[0] for row in _query(f"SELECT id FROM {Figure._meta.db_table} ORDER BY id")]
    # Sources in a fixed order, so the IDU wording does not depend on the database's row order.
    sources = _query(
        f"""
        SELECT figure_source.figure_id, org.name, kind.name, kind.reliability
        FROM {Figure.sources.through._meta.db_table} figure_source
        JOIN {Organization._meta.db_table} org ON org.id = figure_source.organization_id
        LEFT JOIN {OrganizationKind._meta.db_table} kind ON kind.id = org.organization_kind_id
        ORDER BY figure_source.figure_id, figure_source.organization_id
        """
    )
    sources_by_figure = itertools.groupby(sources, key=lambda row: row[0])
    next_group = next(sources_by_figure, None)
    for figure_id in figure_ids:
        reliability, wording = "", ""
        if next_group is not None and next_group[0] == figure_id:
            rows = list(next_group[1])
            reliability = _figure_reliability([row[3] for row in rows if row[3] is not None])
            wording = _format_source_before([(name, kind) for _, name, kind, _ in rows])
            next_group = next(sources_by_figure, None)
        yield [figure_id, reliability, wording]


def take_before_snapshot(out_dir, log: Log = no_log) -> typing.Dict[str, int]:
    """The snapshot of the database before the organization migrations (0013, 0014) run."""
    if _is_migrated():
        raise CommandError(
            "The organization migrations have already run: 0014 dropped the kind's reliability column, so the "
            "before snapshot can no longer be taken. Take it before running migrate."
        )
    return _take(
        out_dir,
        [
            (
                "organizations",
                ORGANIZATIONS_FILE,
                ORGANIZATION_ROW,
                BEFORE_ORGANIZATION_COLUMNS,
                _organization_rows_before(),
            ),
            ("figures", FIGURES_FILE, FIGURE_ROW, BEFORE_FIGURE_COLUMNS, _figure_rows_before()),
        ],
        log,
    )
