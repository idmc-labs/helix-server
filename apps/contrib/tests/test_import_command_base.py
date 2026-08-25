"""
Coverage for the parts of `BaseImportCommand` no shipped importer exercises.

`CodeLookup` and list-valued columns are framework features, but the only importer that used them
narrowed its editable surface, which would leave both untested. The importer below exists purely to
drive them: it is defined here rather than registered as a management command, and `handle()` is
called directly, which is the same entry point `call_command` reaches.
"""

import tempfile
from io import StringIO

from django.core.management.base import CommandError, OutputWrapper
from openpyxl import Workbook
from rest_framework import serializers

from apps.contrib.management.base import (
    BaseImportCommand,
    CodeLookup,
    EnumLookup,
)
from apps.country.models import Country
from apps.entry.models import FigureLocation
from utils.factories import CountryFactory, FigureLocationFactory
from utils.tests import HelixTestCase


def write_sheet(headers, rows, sheet_name="Data"):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.get(header) for header in headers])
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    workbook.save(tmp.name)
    return tmp.name


class WideLocationSerializer(serializers.ModelSerializer):
    """A code column and a list column, which is all these tests need."""

    class Meta:
        model = FigureLocation
        fields = ["id", "country_code", "bounding_box", "accuracy"]


class WideLocationImportCommand(BaseImportCommand):
    model = FigureLocation
    update_serializer = WideLocationSerializer
    update_only = True

    lookups = [
        EnumLookup("accuracy", FigureLocation.ACCURACY),
        CodeLookup("country_code", Country, "iso2"),
    ]


class TestImportCommandBase(HelixTestCase):
    def run_import(self, path):
        """Drive the unregistered command through its real entry point, capturing its output."""
        command = WideLocationImportCommand()
        command.stdout = OutputWrapper(StringIO())
        command.stderr = OutputWrapper(StringIO())
        command.handle(file_path=path, user_email=None, dry_run=False, make_template=None)
        return command.stdout._out.getvalue()

    # ----- CodeLookup -----

    def test_a_code_column_accepts_a_known_code(self):
        CountryFactory.create(name="Ethiopia", iso2="ET", iso3="ETH")
        location = FigureLocationFactory.create(country_code="NP")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": "ET"}])
        self.run_import(path)

        location.refresh_from_db()
        self.assertEqual(location.country_code, "ET")

    def test_a_code_column_rejects_a_code_of_the_wrong_kind(self):
        CountryFactory.create(name="Ethiopia", iso2="ET", iso3="ETH")
        location = FigureLocationFactory.create(country_code="NP")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": "ETH"}])
        with self.assertRaises(CommandError):
            self.run_import(path)

        location.refresh_from_db()
        self.assertEqual(location.country_code, "NP")

    def test_a_code_column_matches_case_insensitively_and_stores_the_canonical_value(self):
        CountryFactory.create(name="Ethiopia", iso2="ET", iso3="ETH")
        location = FigureLocationFactory.create(country_code="NP")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": "et"}])
        self.run_import(path)

        location.refresh_from_db()
        self.assertEqual(location.country_code, "ET")  # the DB's casing, not the sheet's

    def test_an_unknown_code_is_a_row_error(self):
        location = FigureLocationFactory.create(country_code="NP")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": "ZZ"}])
        with self.assertRaises(CommandError):
            self.run_import(path)

    # ----- list-valued columns -----

    def test_a_list_column_splits_a_delimited_cell(self):
        location = FigureLocationFactory.create(bounding_box=None)
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": "1.5;2.5;3.5;4.5"}])
        self.run_import(path)

        location.refresh_from_db()
        self.assertEqual(location.bounding_box, [1.5, 2.5, 3.5, 4.5])

    def test_a_list_column_takes_a_single_value(self):
        location = FigureLocationFactory.create(bounding_box=None)
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": "7.25"}])
        self.run_import(path)

        location.refresh_from_db()
        self.assertEqual(location.bounding_box, [7.25])

    def test_a_list_column_rejects_a_part_that_is_not_a_number(self):
        location = FigureLocationFactory.create(bounding_box=[1.0])
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": "1.5;not-a-number"}])
        with self.assertRaises(CommandError):
            self.run_import(path)

        location.refresh_from_db()
        self.assertEqual(location.bounding_box, [1.0])

    def test_the_clear_token_empties_a_list_column(self):
        location = FigureLocationFactory.create(bounding_box=[1.0, 2.0])
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": "<clear>"}])
        self.run_import(path)

        location.refresh_from_db()
        self.assertIn(location.bounding_box, ([], None))

    # ----- the template describes both kinds of column -----

    def test_the_template_labels_a_code_column_and_a_list_column(self):
        command = WideLocationImportCommand()
        types = command.column_types()

        # A code column matches case-insensitively, so it carries no case note; an enum does.
        self.assertEqual(types["country_code"], "code")
        self.assertEqual(types["bounding_box"], "number list")
        self.assertEqual(types["accuracy"], "single choice, case-sensitive")
