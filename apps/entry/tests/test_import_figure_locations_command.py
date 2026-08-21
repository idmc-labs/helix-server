import tempfile
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import Workbook, load_workbook

from apps.entry.models import FigureLocation
from apps.entry.serializers import FigureLocationSerializer
from utils.factories import CountryFactory, FigureLocationFactory
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

    def template_headers(self):
        out = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        call_command("import_figure_locations", "--make-template", out.name)
        return [cell.value for cell in load_workbook(out.name)["Data"][1]]

    def test_template_exposes_expected_columns(self):
        # Pinned in full and in order: importable columns come from a denylist, so adding a
        # FigureLocation field fails here until someone decides to expose or exclude it.
        self.assertEqual(
            self.template_headers(),
            [
                "id",
                "country",
                "geocoder",
                "country_code",
                "wikipedia",
                "rank",
                "street",
                "wiki_data",
                "osm_id",
                "osm_type",
                "house_numbers",
                "identifier",
                "city",
                "display_name",
                "lon",
                "lat",
                "state",
                "bounding_box",
                "type",
                "importance",
                "class_name",
                "name",
                "name_suffix",
                "place_rank",
                "alternative_names",
                "accuracy",
                "pcode",
                "pcode_source",
                "pcode_accuracy",
            ],
        )

    def test_template_hides_denylisted_columns(self):
        headers = self.template_headers()
        for hidden in ["uuid", "geocoder_metadata", "moved", "created_by", "created_at", "old_id"]:
            self.assertNotIn(hidden, headers)

    def test_denylisted_column_rejected_on_import(self):
        location = FigureLocationFactory.create()
        original_uuid = location.uuid
        path = write_sheet(["id", "uuid"], [{"id": location.id, "uuid": "0" * 32}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertEqual(location.uuid, original_uuid)

    def test_updates_multiple_fields_in_one_row(self):
        CountryFactory.create(name="Ethiopia", iso2="ET", iso3="ETH")
        location = FigureLocationFactory.create(display_name="Old Name", pcode="OLD")
        path = write_sheet(
            ["id", "display_name", "city", "state", "country", "country_code", "lat", "lon", "pcode"],
            [
                {
                    "id": location.id,
                    "display_name": "Addis Ababa, Ethiopia",
                    "city": "Addis Ababa",
                    "state": "Addis Ababa",
                    "country": "Ethiopia",
                    "country_code": "ET",
                    "lat": 9.03,
                    "lon": 38.74,
                    "pcode": "ET0102",
                }
            ],
        )
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.display_name, "Addis Ababa, Ethiopia")
        self.assertEqual(location.city, "Addis Ababa")
        self.assertEqual(location.state, "Addis Ababa")
        self.assertEqual(location.country, "Ethiopia")
        self.assertEqual(location.country_code, "ET")
        self.assertEqual(location.lat, 9.03)
        self.assertEqual(location.lon, 38.74)
        self.assertEqual(location.pcode, "ET0102")

    def test_geocoding_enums_resolve_by_name(self):
        location = FigureLocationFactory.create()
        path = write_sheet(
            ["id", "accuracy", "identifier", "geocoder"],
            [{"id": location.id, "accuracy": "ADM2", "identifier": "DESTINATION", "geocoder": "GEONAME"}],
        )
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.accuracy, FigureLocation.ACCURACY.ADM2.value)
        self.assertEqual(location.identifier, FigureLocation.IDENTIFIER.DESTINATION.value)
        self.assertEqual(location.geocoder, FigureLocation.GEOCODER.GEONAME.value)

    def test_bad_geocoder_enum_rejected(self):
        location = FigureLocationFactory.create(geocoder=FigureLocation.GEOCODER.OSMNAME)
        path = write_sheet(["id", "geocoder"], [{"id": location.id, "geocoder": "NOT_A_GEOCODER"}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertEqual(location.geocoder, FigureLocation.GEOCODER.OSMNAME.value)

    def test_bounding_box_parses_delimited_floats(self):
        location = FigureLocationFactory.create()
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": "8.8; 9.2;38.6 ;39.1"}])
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.bounding_box, [8.8, 9.2, 38.6, 39.1])

    def test_bounding_box_rejects_non_number(self):
        # The base only splits the cell; the serializer's child field coerces each part, so the
        # error names the offending position rather than the whole cell.
        location = FigureLocationFactory.create(bounding_box=[1.0, 2.0])
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": "8.8;north;39.1"}])
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path, stdout=out)
        self.assertIn("A valid number is required", out.getvalue())
        location.refresh_from_db()
        self.assertEqual(location.bounding_box, [1.0, 2.0])

    def test_bounding_box_single_value_cell(self):
        # A one-number cell arrives from openpyxl as a float, not a string.
        location = FigureLocationFactory.create()
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": 8.8}])
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.bounding_box, [8.8])

    def test_bounding_box_clear_token_nulls(self):
        # NULL is how an absent bounding box is stored; an empty array is not used.
        location = FigureLocationFactory.create(bounding_box=[1.0, 2.0, 3.0, 4.0])
        path = write_sheet(["id", "bounding_box"], [{"id": location.id, "bounding_box": "<clear>"}])
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertIsNone(location.bounding_box)

    def test_country_code_must_be_a_known_iso2(self):
        CountryFactory.create(name="Ethiopia", iso2="ET", iso3="ETH")
        location = FigureLocationFactory.create(country_code="ET")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": "XX"}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertEqual(location.country_code, "ET")

    def test_country_code_iso3_rejected(self):
        # The column stores an iso2; an iso3 for the same country is still wrong.
        CountryFactory.create(name="Ethiopia", iso2="ET", iso3="ETH")
        location = FigureLocationFactory.create(country_code="ET")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": "ETH"}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertEqual(location.country_code, "ET")

    def test_country_code_matched_case_insensitively_and_stored_canonically(self):
        # Existing rows are mostly lowercase, so input casing must be accepted; the value
        # stored is the one Country carries, not the operator's.
        CountryFactory.create(name="Ethiopia", iso2="ET", iso3="ETH")
        location = FigureLocationFactory.create(country_code="np")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": " et "}])
        call_command("import_figure_locations", path)

        location.refresh_from_db()
        self.assertEqual(location.country_code, "ET")

    def test_country_code_over_max_length_is_row_error(self):
        # The importer's iso2 lookup rejects this first, but the serializer must also carry
        # max_length itself: without it an over-long value from any other caller reaches the
        # varchar(8) column and raises DataError instead of a validation error.
        serializer = FigureLocationSerializer(data={"country_code": "ETHIOPIA-ET"}, partial=True)
        serializer.is_valid()
        self.assertIn("country_code", serializer.errors)

        location = FigureLocationFactory.create(country_code="ET")
        path = write_sheet(["id", "country_code"], [{"id": location.id, "country_code": "ETHIOPIA-ET"}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertEqual(location.country_code, "ET")

    def test_clear_on_non_nullable_field_is_row_error(self):
        location = FigureLocationFactory.create(display_name="Keep Me")
        path = write_sheet(["id", "display_name"], [{"id": location.id, "display_name": "<clear>"}])
        with self.assertRaises(CommandError):
            call_command("import_figure_locations", path)
        location.refresh_from_db()
        self.assertEqual(location.display_name, "Keep Me")
