"""Snapshot the GIDD published figures, and check the published wording."""

import csv
import json
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from apps.gidd.tests import test_export_source_types
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

    # Borrowed through the module, not imported or inherited, so pytest does not collect that
    # file's tests a second time here.
    setUp = test_export_source_types.GiddExportSourceTypeTestCase.setUp
    generate = test_export_source_types.GiddExportSourceTypeTestCase.generate
    figure_with_sources = test_export_source_types.GiddExportSourceTypeTestCase.figure_with_sources

    def test_snapshot_of_generated_figures(self):
        figure = self.figure_with_sources()
        self.generate(figure)
        # The output directory does not exist yet: the command creates it.
        output_dir = os.path.join(tempfile.mkdtemp(), "before")
        call_command("snapshot_gidd_figures", output_dir=output_dir, stdout=StringIO())
        path = os.path.join(output_dir, "gidd_figures.csv")

        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], f"{figure.id}:2018")
        self.assertEqual(json.loads(rows[0]["sources"]), ["Alpha Agency", "Beta Bureau"])
        self.assertEqual(json.loads(rows[0]["sources_type"]), [None, "Media"])

    def test_before_snapshot_without_subtype_column(self):
        figure = self.figure_with_sources()
        self.generate(figure)
        # Before gidd 0047 the table has no sources_sub_type column (rolled back after the test).
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute("ALTER TABLE gidd_giddfigure DROP COLUMN sources_sub_type")
        output_dir = os.path.join(tempfile.mkdtemp(), "before")
        call_command("snapshot_gidd_figures", output_dir=output_dir, before=True, stdout=StringIO())

        rows = list(csv.DictReader(open(os.path.join(output_dir, "gidd_figures.csv"), encoding="utf-8")))
        self.assertEqual(len(rows), 1)
        self.assertNotIn("sources_sub_type", rows[0])
        self.assertEqual(json.loads(rows[0]["sources_type"]), [None, "Media"])

    def test_before_refused_once_migrated(self):
        with self.assertRaisesMessage(CommandError, "gidd 0047 has already run"):
            call_command("snapshot_gidd_figures", output_dir=tempfile.mkdtemp(), before=True, stdout=StringIO())

    def test_after_refused_before_migrating(self):
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute("ALTER TABLE gidd_giddfigure DROP COLUMN sources_sub_type")
        with self.assertRaisesMessage(CommandError, "gidd 0047 has not run yet"):
            call_command("snapshot_gidd_figures", output_dir=tempfile.mkdtemp(), stdout=StringIO())
