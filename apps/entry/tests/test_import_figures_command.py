import tempfile
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import Workbook, load_workbook

from apps.entry.management.commands.import_figures import Command as ImportFiguresCommand
from apps.entry.models import DisaggregatedAge, Figure
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
        for field in ("geo_locations", "disaggregation_age", "entry", "country", "tags", "sources"):
            self.assertNotIn(field, columns)
        self.assertIn("event", columns)

    def test_both_keys_lead_the_columns(self):
        columns = ImportFiguresCommand().import_columns()
        self.assertEqual(columns[:2], ["id", "uuid"])
        # Neither key is required on its own: a row supplies exactly one.
        self.assertEqual(ImportFiguresCommand().required_create_columns(), set())

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

    # ----- a template an operator has edited -----
    #
    # Sheets arrive reordered, stripped of columns, and with the README gone. Only an unknown
    # column or a missing key should stop an import; nothing else may silently misread a row.

    def test_the_readme_sheet_is_not_required(self):
        # --make-template writes README + Data; an operator may keep only the data.
        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        workbook = load_workbook(path)
        self.assertEqual(workbook.sheetnames, ["Data"])  # write_sheet already omits README

        call_command("import_figures", path)
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)

    def test_extra_sheets_are_ignored_and_data_is_found_by_name(self):
        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        workbook = load_workbook(path)
        readme = workbook.create_sheet("README", 0)  # placed first, so it is the active sheet
        readme["A1"] = "Instructions an operator left in place"
        workbook.save(path)

        call_command("import_figures", path)
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)

    def test_columns_may_be_dropped(self):
        # Only two of the 41 columns are kept.
        path = write_sheet(["uuid", "reported"], [{"uuid": str(self.figure.uuid), "reported": 250}])
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)
        self.assertEqual(self.figure.calculation_logic, "Original logic.")

    def test_columns_may_be_reordered(self):
        path = write_sheet(
            ["calculation_logic", "reported", "id"],
            [{"id": self.figure.id, "reported": 250, "calculation_logic": "Reordered."}],
        )
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)
        self.assertEqual(self.figure.calculation_logic, "Reordered.")

    def test_a_sheet_of_only_the_key_column_changes_nothing(self):
        path = write_sheet(["id"], [{"id": self.figure.id}])
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.assertIn("1 of the updated rows had no effective change.", out.getvalue())
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    def test_dropping_every_key_column_is_refused(self):
        # The one thing an operator may not remove.
        path = write_sheet(["reported"], [{"reported": 250}])
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn("exactly one of id · uuid is required; none given", out.getvalue())
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    def test_three_data_rows_update_exactly_three_figures(self):
        # The header is consumed by read_rows while apply_rows numbers rows from 2, so the count
        # and the reported row numbers are two separate chances to be off by one.
        second = self._second_figure()
        third = self._second_figure()
        figures = [self.figure, second, third]
        path = write_sheet(
            ["id", "reported"],
            [{"id": figure.id, "reported": 300 + index} for index, figure in enumerate(figures)],
        )
        out = StringIO()
        call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.assertIn("Created 0, updated 3.", output)
        for index, figure in enumerate(figures):
            figure.refresh_from_db()
            self.assertEqual(figure.reported, 300 + index)

        # Exactly three changelog lines, numbered 2, 3, 4 — never 1, and never a fourth.
        changed = [line for line in output.splitlines() if line.startswith("ROW_UPDATED")]
        self.assertEqual(len(changed), 3)
        self.assertEqual(
            sorted(line.split("\trow=")[1].split("\t")[0] for line in changed),
            ["2", "3", "4"],
        )

    def test_a_row_number_in_an_error_points_at_the_offending_sheet_row(self):
        # Same off-by-one risk on the error path: the third data row is sheet row 4.
        second = self._second_figure()
        path = write_sheet(
            ["id", "reported"],
            [
                {"id": self.figure.id, "reported": 300},
                {"id": second.id, "reported": 301},
                {"id": 9999999, "reported": 302},
            ],
        )
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn("Row 4: id: no Figure found with id 9999999", out.getvalue())

    def test_a_header_only_sheet_imports_nothing(self):
        path = write_sheet(["id", "reported"], [])
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.assertIn("Created 0, updated 0.", out.getvalue())

    def test_a_blank_row_between_rows_is_skipped(self):
        other = self._second_figure()
        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        workbook = load_workbook(path)
        worksheet = workbook["Data"]
        worksheet.append([None, None])
        worksheet.append([other.id, 800])
        workbook.save(path)

        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.assertIn("Created 0, updated 2.", out.getvalue())
        self.figure.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)
        self.assertEqual(other.reported, 800)

    def test_a_cleared_header_cell_is_refused_rather_than_shifting_the_columns(self):
        # Clearing a header cell but leaving its column is an easy slip in Excel. Dropping the
        # blank would read reported against the household_size cell and write 6.0 over 250.
        path = write_sheet(
            ["id", "household_size", "reported"],
            [{"id": self.figure.id, "household_size": 6.0, "reported": 250}],
        )
        workbook = load_workbook(path)
        workbook["Data"]["B1"] = None  # header cleared, column still there
        workbook.save(path)

        with self.assertRaises(CommandError) as caught:
            call_command("import_figures", path, stdout=StringIO())

        self.assertIn("Column(s) B have no header", str(caught.exception))
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    def test_a_trailing_blank_header_over_an_empty_column_is_tolerated(self):
        # Stray formatting past the data is not an error: nothing follows it to misalign.
        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        workbook = load_workbook(path)
        workbook["Data"]["D1"] = "   "
        workbook.save(path)

        call_command("import_figures", path)
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)

    def test_a_value_in_an_unheaded_column_is_refused(self):
        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        workbook = load_workbook(path)
        workbook["Data"]["D2"] = "orphaned value"  # no header above it
        workbook.save(path)

        with self.assertRaises(CommandError) as caught:
            call_command("import_figures", path, stdout=StringIO())

        self.assertIn("the header row does not name", str(caught.exception))
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    # ----- what the log says, and what the serializer overrides -----

    def test_a_duplicated_header_is_refused(self):
        # zip() pairs a header with the cell below it, so a repeated header would keep one cell and
        # drop the other in silence.
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Data"
        worksheet.append(["id", "reported", "reported"])
        worksheet.append([self.figure.id, 250, None])
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        workbook.save(tmp.name)

        with self.assertRaises(CommandError) as caught:
            call_command("import_figures", tmp.name, stdout=StringIO())

        self.assertIn("Duplicate column(s): reported", str(caught.exception))
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    def test_a_date_formatted_cell_is_accepted(self):
        # A spreadsheet has no date type distinct from datetime, so openpyxl hands back a datetime.
        path = write_sheet(["id", "start_date"], [{"id": self.figure.id, "start_date": date(2020, 6, 15)}])
        call_command("import_figures", path, stdout=StringIO())

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.start_date, date(2020, 6, 15))

    def test_an_enum_change_reports_the_member_name(self):
        Figure.objects.filter(pk=self.figure.pk).update(role=Figure.ROLE.TRIANGULATION)
        path = write_sheet(["id", "role"], [{"id": self.figure.id, "role": "RECOMMENDED"}])
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.role, Figure.ROLE.RECOMMENDED.value)
        # The member name, not the translated label: labels are not unique and cannot be grepped
        # for the token the sheet wrote.
        self.assertIn("role=TRIANGULATION->RECOMMENDED", out.getvalue())

    def test_two_long_values_that_cut_to_the_same_text_report_no_values(self):
        self.figure.calculation_logic = "x" * 200 + "OLD"
        self.figure.save()
        path = write_sheet(
            ["id", "calculation_logic"],
            [{"id": self.figure.id, "calculation_logic": "x" * 200 + "NEW"}],
        )
        out = StringIO()
        call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.figure.refresh_from_db()
        self.assertTrue(self.figure.calculation_logic.endswith("NEW"))
        # Quoting both would show a change from a value to itself, so the field is named instead.
        self.assertIn("calculation_logic=changed", output)
        self.assertNotIn("->", output.split("calculation_logic=")[1].split("\t")[0])

    def test_two_long_values_that_still_differ_when_cut_report_both(self):
        self.figure.calculation_logic = "OLD " + "x" * 200
        self.figure.save()
        path = write_sheet(
            ["id", "calculation_logic"],
            [{"id": self.figure.id, "calculation_logic": "NEW " + "x" * 200}],
        )
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        # The cut is harmless here: the two are still told apart, so both are shown.
        self.assertIn("calculation_logic=OLD ", out.getvalue())
        self.assertIn("->NEW ", out.getvalue())

    def test_a_cell_the_serializer_empties_is_reported_as_ignored(self):
        # IDPS is a stock category, so the serializer clears end_date_accuracy whatever the sheet
        # says. The row is still updated; the discarded cell must not vanish in silence.
        self.figure.end_date_accuracy = None
        self.figure.save()
        path = write_sheet(
            ["id", "reported", "end_date_accuracy"],
            [{"id": self.figure.id, "reported": 250, "end_date_accuracy": "MONTH"}],
        )
        out = StringIO()
        call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)
        self.assertIsNone(self.figure.end_date_accuracy)
        self.assertIn("CELL_IGNORED\trow=2\tend_date_accuracy=MONTH", output)
        self.assertIn("cell(s) were ignored", output)

    def test_a_deliberately_cleared_cell_is_not_reported_as_ignored(self):
        self.figure.source_excerpt = "Some excerpt."
        self.figure.save()
        path = write_sheet(["id", "source_excerpt"], [{"id": self.figure.id, "source_excerpt": "<clear>"}])
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.figure.refresh_from_db()
        self.assertFalse(self.figure.source_excerpt)
        self.assertNotIn("CELL_IGNORED", out.getvalue())

    def test_an_injected_write_to_an_excluded_field_is_still_reported(self):
        # disaggregation_age is kept out of the columns, but the serializer empties it whenever
        # is_disaggregated is unset. Being un-editable is not a reason to leave the write unlogged.
        age = DisaggregatedAge.objects.create(sex=1, value=10, age_from=0, age_to=5)
        self.figure.disaggregation_age.set([age])
        self.figure.is_disaggregated = False
        self.figure.save()

        path = write_sheet(["id", "reported"], [{"id": self.figure.id, "reported": 250}])
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.disaggregation_age.count(), 0)
        self.assertIn(f"disaggregation_age=[{age.pk}]->[]", out.getvalue())

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

    # ----- naming a row by id or by uuid -----

    def test_a_row_identified_by_uuid_patches_that_figure(self):
        other = self._second_figure()
        path = write_sheet(["uuid", "reported"], [{"uuid": str(self.figure.uuid), "reported": 250}])
        call_command("import_figures", path)

        self.figure.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.figure.reported, 250)
        self.assertEqual(other.reported, 700)  # the other figure is untouched

    def test_an_unknown_uuid_fails_the_row(self):
        path = write_sheet(
            ["uuid", "reported"],
            [{"uuid": "4a1c9f2e-0000-4000-8000-000000000000", "reported": 250}],
        )
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn("no Figure found with uuid 4a1c9f2e-0000-4000-8000-000000000000", out.getvalue())
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    def test_supplying_both_keys_fails_the_row(self):
        path = write_sheet(
            ["id", "uuid", "reported"],
            [{"id": self.figure.id, "uuid": str(self.figure.uuid), "reported": 250}],
        )
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        # Rejected even though the two keys agree: a row names a figure one way.
        self.assertIn("exactly one of id · uuid is required; 2 given", out.getvalue())
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    def test_supplying_neither_key_fails_the_row(self):
        path = write_sheet(["id", "uuid", "reported"], [{"id": None, "uuid": None, "reported": 250}])
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.assertIn("exactly one of id · uuid is required; none given", output)
        self.assertIn("only updates existing Figure rows", output)
        self.assertEqual(Figure.objects.count(), 1)

    def test_a_uuid_shared_by_two_figures_fails_the_row(self):
        # Figure.uuid lost its unique constraint in 2021 and helix stores uuids it did not
        # generate, so a shared uuid is possible and must not resolve to an arbitrary figure.
        shared = self.figure.uuid
        twin = self._second_figure()
        Figure.objects.filter(pk=twin.pk).update(uuid=shared)

        path = write_sheet(["uuid", "reported"], [{"uuid": str(shared), "reported": 250}])
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)
        output = out.getvalue()

        self.assertIn(f"uuid {shared} matches more than one Figure", output)
        self.assertIn(str(self.figure.pk), output)
        self.assertIn(str(twin.pk), output)
        self.figure.refresh_from_db()
        twin.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)
        self.assertEqual(twin.reported, 700)

    def test_one_figure_named_by_id_on_one_row_and_uuid_on_another_is_a_duplicate(self):
        # The duplicate check keys on the resolved figure, so it catches a collision the two
        # sheets' key columns disguise.
        path = write_sheet(
            ["id", "uuid", "reported"],
            [
                {"id": self.figure.id, "uuid": None, "reported": 250},
                {"id": None, "uuid": str(self.figure.uuid), "reported": 300},
            ],
        )
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("import_figures", path, stdout=out)

        self.assertIn(f"Figure {self.figure.id} also appears on row 2", out.getvalue())
        self.figure.refresh_from_db()
        self.assertEqual(self.figure.reported, 100)

    def test_a_uuid_keyed_edit_leaves_the_uuid_alone(self):
        # uuid is a key, not data: hulk holds the same value on its own row, so this importer
        # must never write it.
        original = self.figure.uuid
        path = write_sheet(["uuid", "reported"], [{"uuid": str(original), "reported": 250}])
        out = StringIO()
        call_command("import_figures", path, stdout=out)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.uuid, original)
        self.assertEqual(self.figure.reported, 250)
        # The key never shows up as a change, and neither does the injected id.
        self.assertNotIn("uuid=", out.getvalue())
        self.assertNotIn("id=", out.getvalue())

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
