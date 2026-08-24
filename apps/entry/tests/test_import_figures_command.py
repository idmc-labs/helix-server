import tempfile
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import Workbook, load_workbook

from apps.entry.management.commands.import_figures import Command as ImportFiguresCommand
from apps.entry.models import Figure
from apps.entry.serializers import FigureSerializer
from utils.factories import CountryFactory, EventFactory, FigureFactory
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


class TestImportFiguresCommand(HelixTestCase):
    def setUp(self):
        super().setUp()
        self.country = CountryFactory.create(iso3="NPL", iso2="NP")
        self.event = EventFactory.create(countries=[self.country])
        self.figure = FigureFactory.create(
            event=self.event,
            country=self.country,
            unit=Figure.UNIT.PERSON,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            start_date=date(2020, 6, 1),
            end_date=date(2020, 6, 30),
            reported=100,
            total_figures=100,
            calculation_logic="Original logic.",
            # The factory sets a household size regardless of unit; a person-unit figure holds
            # none, and leaving the factory's value in would make every edit null it as a
            # serializer side effect and muddy what each test is asserting.
            household_size=None,
        )

    # ----- core edit path -----

    def test_a_row_patches_the_named_fields(self):
        path = write_sheet(
            ["id", "reported", "calculation_logic"],
            [{"id": self.figure.id, "reported": 250, "calculation_logic": "Revised logic."}],
        )
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)
        self.assertEqual(self.figure.calculation_logic, "Revised logic.")
        # total_figures is derived from reported for a person-unit figure.
        self.assertEqual(self.figure.total_figures, 250)
        self.assertEqual(Figure.objects.count(), 1)  # updated, not created

    def test_a_blank_cell_leaves_the_field_unchanged(self):
        path = write_sheet(
            ["id", "reported", "calculation_logic"],
            [{"id": self.figure.id, "reported": 250, "calculation_logic": None}],
        )
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)
        self.assertEqual(self.figure.calculation_logic, "Original logic.")

    def test_the_clear_token_clears_a_nullable_field(self):
        self.figure.source_excerpt = "Some excerpt."
        self.figure.save()

        path = write_sheet(
            ["id", "source_excerpt"],
            [{"id": self.figure.id, "source_excerpt": "<clear>"}],
        )
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        self.assertFalse(self.figure.source_excerpt)

    def test_enum_columns_resolve_by_member_name(self):
        path = write_sheet(
            ["id", "role", "category"],
            [{"id": self.figure.id, "role": "RECOMMENDED", "category": "RETURN"}],
        )
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.role, Figure.ROLE.RECOMMENDED.value)
        self.assertEqual(self.figure.category, Figure.FIGURE_CATEGORY_TYPES.RETURN.value)

    def test_an_unknown_enum_value_fails_the_row(self):
        original_role = self.figure.role
        path = write_sheet(["id", "role"], [{"id": self.figure.id, "role": "NOT_A_ROLE"}])
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn("invalid value 'NOT_A_ROLE'", out.getvalue())
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.role, original_role)

    def test_event_resolves_by_id(self):
        other_event = EventFactory.create(countries=[self.country])
        path = write_sheet(["id", "event"], [{"id": self.figure.id, "event": other_event.id}])
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.event_id, other_event.id)

    def test_an_unknown_event_id_fails_the_row(self):
        path = write_sheet(["id", "event"], [{"id": self.figure.id, "event": 9999999}])
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=StringIO())

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.event_id, self.event.id)

    def test_blank_id_rejected_no_create(self):
        # update-only: a row without an id must fail loudly rather than create an orphan figure.
        path = write_sheet(["id", "reported"], [{"id": None, "reported": 5}])
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn("only updates existing Figure rows", out.getvalue())
        self.assertEqual(Figure.objects.count(), 1)

    def test_an_unknown_id_fails_the_row(self):
        path = write_sheet(["id", "reported"], [{"id": 9999999, "reported": 5}])
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn("no Figure found with id 9999999", out.getvalue())

    def test_dry_run_rolls_back(self):
        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        out = StringIO()
        call_command("import_figures", path, dry_run=True, stdout=out)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)
        self.assertIn("DRY RUN", out.getvalue())

    # ----- denylist and template -----

    def test_denylisted_fields_are_not_columns(self):
        columns = ImportFiguresCommand().import_columns()
        for field in ("geo_locations", "disaggregation_age", "uuid", "entry", "country", "tags", "sources"):
            self.assertNotIn(field, columns)
        self.assertIn("id", columns)
        self.assertIn("event", columns)

    def test_a_sheet_naming_a_denylisted_column_is_rejected(self):
        path = write_sheet(["id", "country"], [{"id": self.figure.id, "country": self.country.id}])
        with self.assertRaises(CommandError) as caught:
            call_command("import_figures", path, stdout=StringIO())

        self.assertIn("Unknown column(s): country", str(caught.exception))

    def test_make_template_writes_the_expected_columns(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        call_command("import_figures", make_template=tmp.name, stdout=StringIO())

        workbook = load_workbook(tmp.name)
        self.assertIn("Data", workbook.sheetnames)
        headers = [cell.value for cell in workbook["Data"][1]]
        self.assertEqual(headers, ImportFiguresCommand().import_columns())
        self.assertEqual(headers[0], "id")

    # ----- changelog and duplicates -----

    def test_the_changelog_names_only_the_fields_that_moved(self):
        path = write_sheet(
            ["id", "reported", "calculation_logic"],
            [{"id": self.figure.id, "reported": 250, "calculation_logic": "Original logic."}],
        )
        out = StringIO()
        call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.assertIn(f"ROW_UPDATED\tfigure={self.figure.id}\trow=2", output)
        self.assertIn("reported=100->250", output)
        # Supplied but identical, so it did not move and is not reported.
        self.assertNotIn("calculation_logic=", output)

    def test_a_row_that_changes_nothing_reports_no_changelog_line(self):
        # Applying the same sheet twice: the second run has nothing left to move, so it reports no
        # changelog line at all. Re-importing is how an operator retries, so it must be quiet.
        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        call_command("import_figures", path, stdout=StringIO())

        out = StringIO()
        call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.assertNotIn("ROW_UPDATED", output)
        self.assertIn("1 of the updated rows had no effective change.", output)

    def test_the_changelog_reports_serializer_injected_writes(self):
        # The serializer nulls disaggregation values whenever is_disaggregated is not set, even on
        # an edit that never mentions them. The changelog is the only place that surfaces it.
        self.figure.is_disaggregated = False
        self.figure.disaggregation_sex_male = 40
        self.figure.save()

        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.assertIn("disaggregation_sex_male=40->None", out.getvalue())
        self.figure.refresh_from_db()
        self.assertIsNone(self.figure.disaggregation_sex_male)

    def test_a_multi_line_value_stays_on_one_changelog_line(self):
        self.figure.calculation_logic = "First line.\n\nSecond line."
        self.figure.save()

        path = write_sheet(
            ["id", "calculation_logic"],
            [{"id": self.figure.id, "calculation_logic": "Flat."}],
        )
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        changelog_lines = [line for line in out.getvalue().splitlines() if line.startswith("ROW_UPDATED")]
        self.assertEqual(len(changelog_lines), 1)
        self.assertIn("calculation_logic=First line. Second line.->Flat.", changelog_lines[0])

    def test_a_long_value_is_cut_so_the_line_stays_readable(self):
        self.figure.calculation_logic = "x" * 500
        self.figure.save()

        path = write_sheet(["id", "calculation_logic"], [{"id": self.figure.id, "calculation_logic": "Short."}])
        out = StringIO()
        call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.assertIn("x" * ImportFiguresCommand.CHANGELOG_VALUE_CHARS + "...", output)
        self.assertNotIn("x" * (ImportFiguresCommand.CHANGELOG_VALUE_CHARS + 1), output)

    def test_a_duplicate_id_fails_naming_both_rows(self):
        path = write_sheet(
            ["id", "reported"],
            [{"id": self.figure.id, "reported": 250}, {"id": self.figure.id, "reported": 300}],
        )
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.assertIn(f"Row 3: id: Figure {self.figure.id} also appears on row 2", output)
        # All-or-nothing: the first row is not applied either.
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    # ----- all-or-nothing -----
    #
    # Unlike the bulk figure mutation, which wraps save_item per item and reports the rest in
    # failure_list, this importer commits every row or none. The two tests below pin each half of
    # that: a row rejected during validation, and a row that breaks while being saved.

    def _second_figure(self):
        return FigureFactory.create(
            event=self.event,
            country=self.country,
            unit=Figure.UNIT.PERSON,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            start_date=date(2020, 6, 1),
            end_date=date(2020, 6, 30),
            reported=700,
            total_figures=700,
            household_size=None,
        )

    def test_one_invalid_row_leaves_every_other_row_unapplied(self):
        other = self._second_figure()
        path = write_sheet(
            ["id", "reported", "role"],
            [
                {"id": self.figure.id, "reported": 250},
                {"id": other.id, "reported": 800},
                {"id": self.figure.id + other.id + 1000, "reported": 1},  # no such figure
            ],
        )
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn("nothing committed", out.getvalue())
        self.figure.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)
        self.assertEqual(other.reported, 700)

    def test_a_failure_while_saving_rolls_back_the_rows_already_saved(self):
        # Validation passed for every row, so this is the case per-item isolation would paper over:
        # the first row is already written when the second breaks.
        other = self._second_figure()
        path = write_sheet(
            ["id", "reported"],
            [{"id": self.figure.id, "reported": 250}, {"id": other.id, "reported": 800}],
        )

        real_save = FigureSerializer.save
        calls = {"n": 0}

        def failing_save(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("save blew up on the second row")
            return real_save(self, **kwargs)

        with mock.patch.object(FigureSerializer, "save", failing_save):
            with self.assertRaises(RuntimeError):
                call_command("import_figures", path, stdout=StringIO())

        self.assertEqual(calls["n"], 2)
        self.figure.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)
        self.assertEqual(other.reported, 700)
        self.assertEqual(Figure.objects.count(), 2)

    def test_the_importer_is_not_capped_at_the_bulk_operation_threshold(self):
        # The bulk operation refuses more than QUERYSET_COUNT_THRESHOLD (100) figures. An operator
        # backfill is the opposite case, so no such cap applies here.
        from apps.contrib.models import BulkApiOperation

        figures = [self._second_figure() for _ in range(5)]
        path = write_sheet(
            ["id", "reported"],
            [{"id": figure.id, "reported": 900 + index} for index, figure in enumerate(figures)],
        )
        call_command("import_figures", path, stdout=StringIO())

        self.assertGreater(BulkApiOperation.QUERYSET_COUNT_THRESHOLD, len(figures))
        for index, figure in enumerate(figures):
            figure.refresh_from_db()
            self.assertEqual(figure.reported, 900 + index)
