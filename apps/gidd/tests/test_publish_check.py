"""Compare GIDD published figures before and after, and check the published wording."""

import csv
import json
import os
import tempfile
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError

from apps.gidd import publish_check
from apps.gidd.tests.test_export_source_types import GiddExportSourceTypeTestCase
from utils.tests import HelixTestCase, ensure_source_type_taxonomy

COLUMNS = ["key", "figure_raw_id", "year", "sources", "sources_type", "reported"]


def write_snapshot(path, rows, columns=COLUMNS):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def row(figure_id, sources, types, reported=10, **extra):
    return {
        "key": f"{figure_id}:2024",
        "figure_raw_id": figure_id,
        "year": 2024,
        "sources": json.dumps(sources),
        "sources_type": json.dumps(types),
        "reported": reported,
        **{key: json.dumps(value) for key, value in extra.items()},
    }


class TestCompareGiddFigures(HelixTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.before = os.path.join(self.tmp, "before.csv")
        self.after = os.path.join(self.tmp, "after.csv")
        self.out_dir = os.path.join(self.tmp, "out")
        write_snapshot(self.before, [row(1, ["Ministry"], ["Government"]), row(2, ["Paper"], ["Media"])])

    def compare(self):
        call_command("compare_gidd_figures", self.before, self.after, self.out_dir, stdout=StringIO())

    def test_pass_when_only_source_wording_changes(self):
        write_snapshot(
            self.after,
            [
                row(1, ["Ministry"], ["Government"], sources_sub_type=["National Government"]),
                row(2, ["Paper"], ["Media"], sources_sub_type=["Media"]),
            ],
            COLUMNS + ["sources_sub_type"],
        )
        # The type column changes too when an old kind was named differently from its new type.
        write_snapshot(
            self.before,
            [row(1, ["Ministry"], ["Local Authority"]), row(2, ["Paper"], ["Media"])],
        )
        self.compare()
        with open(os.path.join(self.out_dir, "report.md"), encoding="utf-8") as f:
            self.assertIn("PASS", f.readline())

    def test_fail_without_subtype_column(self):
        write_snapshot(self.after, [row(1, ["Ministry"], ["Government"]), row(2, ["Paper"], ["Media"])])
        with self.assertRaisesMessage(CommandError, "expected new columns missing: sources_sub_type"):
            self.compare()

    def test_fail_when_another_column_changes(self):
        write_snapshot(
            self.after,
            [
                row(1, ["Ministry"], ["Government"], reported=11, sources_sub_type=["National Government"]),
                row(2, ["Paper"], ["Media"], sources_sub_type=["Media"]),
            ],
            COLUMNS + ["sources_sub_type"],
        )
        with self.assertRaisesMessage(CommandError, "unexpected changes in: reported (1)"):
            self.compare()
        changed = list(csv.DictReader(open(os.path.join(self.out_dir, "changed_cells.csv"), encoding="utf-8")))
        self.assertEqual(changed, [{"key": "1:2024", "column": "reported", "before": "10", "after": "11"}])

    def test_fail_when_rows_differ(self):
        write_snapshot(
            self.after,
            [row(1, ["Ministry"], ["Government"], sources_sub_type=["National Government"])],
            COLUMNS + ["sources_sub_type"],
        )
        with self.assertRaisesMessage(CommandError, "1 rows missing after"):
            self.compare()


class TestCheckGiddSourceWording(HelixTestCase):
    def setUp(self):
        ensure_source_type_taxonomy()
        self.path = os.path.join(tempfile.mkdtemp(), "release.csv")
        self.columns = COLUMNS + ["sources_sub_type"]

    def check(self):
        call_command("check_gidd_source_wording", self.path, stdout=StringIO())

    def test_pass(self):
        # Names from the IDMC taxonomy (migration 0012).
        write_snapshot(
            self.path,
            [row(1, ["Ministry", "Paper"], ["Government", "Media"], sources_sub_type=["Other", "Media"])],
            self.columns,
        )
        self.check()

    def test_fail_on_old_kind_names(self):
        write_snapshot(
            self.path,
            [row(1, ["Ministry"], ["Local Authority"], sources_sub_type=["Local Authority"])],
            self.columns,
        )
        with self.assertRaisesMessage(CommandError, "sources_type values that are not source type names"):
            self.check()

    def test_fail_on_misaligned_lists(self):
        write_snapshot(
            self.path,
            [row(1, ["Ministry", "Paper"], ["Government", "Media"], sources_sub_type=["Other"])],
            self.columns,
        )
        with self.assertRaisesMessage(CommandError, "differ in length"):
            self.check()

    def test_fail_without_subtype_column(self):
        write_snapshot(self.path, [row(1, ["Ministry"], ["Government"])])
        with self.assertRaisesMessage(CommandError, "column sources_sub_type is missing"):
            self.check()


class TestSnapshotGiddFigures(HelixTestCase):
    """The snapshot reads the published columns of real generated GIDD figures."""

    # Borrowed, not inherited, so pytest does not collect that file's tests a second time here.
    setUp = GiddExportSourceTypeTestCase.setUp
    generate = GiddExportSourceTypeTestCase.generate
    figure_with_sources = GiddExportSourceTypeTestCase.figure_with_sources

    def test_snapshot_of_generated_figures(self):
        figure = self.figure_with_sources()
        self.generate(figure)
        path = os.path.join(tempfile.mkdtemp(), "snapshot.csv")
        call_command("snapshot_gidd_figures", path, stdout=StringIO())

        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], f"{figure.id}:2018")
        self.assertEqual(json.loads(rows[0]["sources"]), ["Alpha Agency", "Beta Bureau"])
        self.assertEqual(json.loads(rows[0]["sources_type"]), [None, "Media"])

        # The same data snapshotted twice compares equal; it fails only on the missing subtype column.
        with mock.patch.object(publish_check, "ALLOWED_NEW_COLUMNS", set()):
            passed, failures = publish_check.compare_snapshots(path, path, os.path.join(tempfile.mkdtemp(), "out"))
        self.assertTrue(passed, failures)
