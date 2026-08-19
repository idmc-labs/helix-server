import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import Workbook, load_workbook

from apps.entry.models import FigureLocation
from utils.factories import FigureLocationFactory
from utils.tests import HelixTestCase


def write_sheet(headers, rows, sheet_name="Data"):
    """Write a temporary .xlsx with the given headers + rows and return its path."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(headers)
    for row in rows:
        worksheet.append([row.get(header) for header in headers])
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    workbook.save(tmp.name)
    return tmp.name


class TestImportFigureLocationsCommand(HelixTestCase):
    def test_backfill_updates_pcode_fields(self):
        location = FigureLocationFactory.create(display_name="Keep Me")
        path = write_sheet(
            ["id", "pcode", "pcode_source", "pcode_accuracy"],
            [{"id": location.id, "pcode": "ET0102", "pcode_source": "OCHA_COD", "pcode_accuracy": "ADM2"}],
        )
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.pcode, "ET0102")
        self.assertEqual(location.pcode_source, "OCHA_COD")  # free text, stored verbatim
        self.assertEqual(location.pcode_accuracy, FigureLocation.PCODE_ACCURACY.ADM2.value)
        # Backfill leaves untouched fields alone.
        self.assertEqual(location.display_name, "Keep Me")
        self.assertEqual(FigureLocation.objects.count(), 1)  # updated, not created

    def test_pcode_source_is_free_text(self):
        # pcode_source is not an enum: any string (including future, non-canonical
        # sources) is accepted and stored verbatim.
        location = FigureLocationFactory.create()
        path = write_sheet(
            ["id", "pcode_source", "pcode_accuracy"],
            [{"id": location.id, "pcode_source": "SomeFutureSource", "pcode_accuracy": "ADM0"}],
        )
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.pcode_source, "SomeFutureSource")
        self.assertEqual(location.pcode_accuracy, FigureLocation.PCODE_ACCURACY.ADM0.value)

    def test_blank_id_rejected_no_create(self):
        # update-only: a row without an id must fail loudly rather than create an orphan.
        path = write_sheet(
            ["id", "pcode", "pcode_source", "pcode_accuracy"],
            [{"pcode": "ET0102", "pcode_source": "OCHA_COD", "pcode_accuracy": "ADM2"}],
        )
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        self.assertEqual(FigureLocation.objects.count(), 0)

    def test_bad_enum_rejected(self):
        location = FigureLocationFactory.create()
        path = write_sheet(
            ["id", "pcode_accuracy"],
            [{"id": location.id, "pcode_accuracy": "NOT_A_LEVEL"}],
        )
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertIsNone(location.pcode_accuracy)  # nothing committed

    def test_missing_update_target_errors(self):
        path = write_sheet(["id", "pcode"], [{"id": 999999, "pcode": "ET0102"}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)

    def test_blank_pcode_leaves_field_unchanged(self):
        location = FigureLocationFactory.create(pcode="ORIGINAL")
        path = write_sheet(
            ["id", "pcode", "pcode_accuracy"],
            [{"id": location.id, "pcode": "   ", "pcode_accuracy": "ADM3"}],  # blank pcode
        )
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.pcode, "ORIGINAL")  # blank did NOT clear it
        self.assertEqual(location.pcode_accuracy, FigureLocation.PCODE_ACCURACY.ADM3.value)

    def test_clear_token_clears_pcode(self):
        location = FigureLocationFactory.create(pcode="ORIGINAL")
        path = write_sheet(["id", "pcode"], [{"id": location.id, "pcode": "<clear>"}])
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertIsNone(location.pcode)

    def test_template_exposes_only_pcode_columns(self):
        out = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        call_command("import_figure_locations", "--make-template", out.name)

        data_headers = [cell.value for cell in load_workbook(out.name)["Data"][1]]
        self.assertEqual(data_headers, ["id", "pcode", "pcode_source", "pcode_accuracy"])
        # Geocoding fields must not be exposed for a backfill importer.
        for hidden in ["display_name", "lat", "lon", "geocoder", "accuracy", "identifier"]:
            self.assertNotIn(hidden, data_headers)

    def test_unexposed_column_rejected_on_import(self):
        location = FigureLocationFactory.create(display_name="Untouched")
        path = write_sheet(["id", "display_name"], [{"id": location.id, "display_name": "Hacked"}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertEqual(location.display_name, "Untouched")
