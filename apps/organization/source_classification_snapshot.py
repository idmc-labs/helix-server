"""Record each organization's kind and each figure's classification and IDU source wording
before the reclassification, then summarize what changed afterwards.

A snapshot is a directory with two CSV files:
- organizations.csv: organization_id, name, archived, kind_id, kind, source_type, level
- figures.csv: figure_id, classification, idu_source_wording
"""

import csv
import itertools
import os
import typing
from collections import Counter

from apps.entry.models import Figure
from apps.entry.utils import format_source
from apps.organization.models import Organization

ORGANIZATION_COLUMNS = ["organization_id", "name", "archived", "kind_id", "kind", "source_type", "level"]
FIGURE_COLUMNS = ["figure_id", "classification", "idu_source_wording"]
ORGANIZATIONS_FILE = "organizations.csv"
FIGURES_FILE = "figures.csv"
NO_KIND = "(no kind)"


def _write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        count = 0
        for row in rows:
            writer.writerow(["" if value is None else value for value in row])
            count += 1
    return count


def _read_csv(path) -> typing.Dict[str, typing.Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        key = (reader.fieldnames or [""])[0]
        return {row[key]: row for row in reader}


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
        yield [org_id, name, "yes" if deleted_on else "no", kind_id, kind, source_type, level]


def _figure_rows():
    classifications = dict(
        Figure.objects.annotate(**Figure.annotate_sources_classification()).values_list("id", "sources_classification")
    )
    # Sources in a fixed order, so the IDU wording does not depend on the database's row order.
    sources = (
        Figure.sources.through.objects.order_by("figure_id", "organization_id")
        .values_list("figure_id", "organization__name", "organization__organization_kind__name")
        .iterator(chunk_size=5000)
    )
    sources_by_figure = itertools.groupby(sources, key=lambda row: row[0])
    next_group = next(sources_by_figure, None)
    for figure_id in sorted(classifications):
        wording = ""
        if next_group is not None and next_group[0] == figure_id:
            wording = format_source([{"name": name, "organization_kind": kind} for _, name, kind in next_group[1]])
            next_group = next(sources_by_figure, None)
        yield [figure_id, classifications[figure_id], wording]


def take_snapshot(out_dir) -> typing.Dict[str, int]:
    os.makedirs(out_dir, exist_ok=True)
    return {
        "organizations": _write_csv(os.path.join(out_dir, ORGANIZATIONS_FILE), ORGANIZATION_COLUMNS, _organization_rows()),
        "figures": _write_csv(os.path.join(out_dir, FIGURES_FILE), FIGURE_COLUMNS, _figure_rows()),
    }


def _kind_label(row):
    if not row["kind"]:
        return NO_KIND
    return f"{row['source_type']} - {row['kind']}" if row["source_type"] else row["kind"]


def compare_snapshots(before_dir, after_dir, out_dir) -> typing.Dict[str, int]:
    """Write report.md, organizations_moved.csv and figures_changed.csv; return the counts.

    Problems (organizations missing after, or left with no kind) are counted under "problems".
    """
    os.makedirs(out_dir, exist_ok=True)
    orgs_before = _read_csv(os.path.join(before_dir, ORGANIZATIONS_FILE))
    orgs_after = _read_csv(os.path.join(after_dir, ORGANIZATIONS_FILE))
    figures_before = _read_csv(os.path.join(before_dir, FIGURES_FILE))
    figures_after = _read_csv(os.path.join(after_dir, FIGURES_FILE))

    moves: typing.Counter[typing.Tuple[str, str]] = Counter()
    moved_rows, missing_orgs, kindless_orgs = [], [], []
    for org_id, before in orgs_before.items():
        after = orgs_after.get(org_id)
        if after is None:
            missing_orgs.append(org_id)
            continue
        if before["kind"] and not after["kind"]:
            kindless_orgs.append(org_id)
        old, new = _kind_label(before), _kind_label(after)
        if old != new or before["kind_id"] != after["kind_id"]:
            moves[(old, new)] += 1
            moved_rows.append([org_id, before["name"], before["archived"], old, before["level"], new, after["level"]])
    _write_csv(
        os.path.join(out_dir, "organizations_moved.csv"),
        ["organization_id", "name", "archived", "kind_before", "level_before", "kind_after", "level_after"],
        moved_rows,
    )

    level_changes: typing.Counter[typing.Tuple[str, str]] = Counter()
    changed_rows, missing_figures = [], []
    wording_changed = 0
    for figure_id, before in figures_before.items():
        after = figures_after.get(figure_id)
        if after is None:
            missing_figures.append(figure_id)
            continue
        level_changed = before["classification"] != after["classification"]
        text_changed = before["idu_source_wording"] != after["idu_source_wording"]
        if level_changed:
            level_changes[(before["classification"] or "none", after["classification"] or "none")] += 1
        wording_changed += text_changed
        if level_changed or text_changed:
            changed_rows.append(
                [
                    figure_id,
                    before["classification"],
                    after["classification"],
                    before["idu_source_wording"],
                    after["idu_source_wording"],
                ]
            )
    _write_csv(
        os.path.join(out_dir, "figures_changed.csv"),
        ["figure_id", "level_before", "level_after", "idu_source_wording_before", "idu_source_wording_after"],
        changed_rows,
    )

    counts = {
        "organizations": len(orgs_before),
        "organizations_moved": len(moved_rows),
        "figures": len(figures_before),
        "figures_level_changed": sum(level_changes.values()),
        "figures_wording_changed": wording_changed,
        "problems": len(missing_orgs) + len(kindless_orgs),
    }

    lines = [
        "# Source type reclassification summary",
        "",
        f"- Organizations: {counts['organizations']}, moved to another kind: {counts['organizations_moved']}",
        f"- Figures: {counts['figures']}, classification changed: {counts['figures_level_changed']}, "
        f"IDU source wording changed: {counts['figures_wording_changed']}",
        f"- Organizations missing after: {len(missing_orgs)}, left with no kind: {len(kindless_orgs)}",
        f"- Figures missing after: {len(missing_figures)} (deleted between the snapshots)",
        "",
        "## Organizations moved, by kind",
        "",
        "| Before | After | Organizations |",
        "|---|---|---|",
        *[f"| {old} | {new} | {n} |" for (old, new), n in sorted(moves.items())],
        "",
        "## Figure classification changes",
        "",
        "| Level before | Level after | Figures |",
        "|---|---|---|",
        *[f"| {old} | {new} | {n} |" for (old, new), n in sorted(level_changes.items())],
        "",
    ]
    if missing_orgs or kindless_orgs:
        lines += [
            "## Problems",
            "",
            f"- Missing after: {', '.join(missing_orgs) or '-'}",
            f"- Left with no kind: {', '.join(kindless_orgs) or '-'}",
            "",
        ]
    lines.append("Details: organizations_moved.csv, figures_changed.csv")
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return counts
