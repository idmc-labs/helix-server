import csv
import os
import re
import typing
from collections import Counter
from datetime import datetime
from decimal import Decimal
from functools import cached_property
from typing import Union

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from requests.structures import CaseInsensitiveDict

from apps.country.models import Country, HouseholdSize
from apps.country.serializers import HouseholdSizeCliImportSerializer
from apps.entry.models import Figure
from apps.users.models import User
from apps.users.utils import HelixInternalBot
from helix.managers import BulkUpdateManager
from utils.common import round_half_up

DataRow = typing.TypedDict(
    "DataRow",
    {
        "Year": str,
        "AHHS": str,
        "ISO3": str,
        "Data source category": str,
        "Reference date": str,
        "Source": typing.Optional[str],  # We have default value "No data"
        "Source link": typing.Optional[str],  # This should be nullable
        "Notes": typing.Optional[str],
        "IDMC update date": typing.Optional[str],
    },
)


# Figure update modes for --figure-update-mode.
FIGURE_UPDATE_MODE_NONE = "none"  # Touch no figures; import AHHS records only.
FIGURE_UPDATE_MODE_NUMBERS = "numbers"  # Update household_size, total_figures, excerpt_idu.
FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE = "numbers_and_note"  # numbers + append the retroactive calculation_logic note.
FIGURE_UPDATE_MODES = [
    FIGURE_UPDATE_MODE_NONE,
    FIGURE_UPDATE_MODE_NUMBERS,
    FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE,
]

# Data fields that decide whether an incoming AHHS row differs from the current active record.
# Metadata churn fields (created_at/modified_at/created_by/last_modified_by/is_active) are excluded on purpose.
HOUSEHOLD_SIZE_COMPARISON_FIELDS = (
    "size",
    "reference_date",
    "gap_filling_method",
    "data_source_category",
    "source",
    "source_link",
    "notes",
)


def calculate_gap_filling_method(year, reference_year):
    if year == reference_year:
        return HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR
    if year < reference_year:
        return HouseholdSize.GAP_FILLING_METHOD.BACKWARD_FILLING
    return HouseholdSize.GAP_FILLING_METHOD.FORWARD_FILLING


def format_date(date: Union[str, datetime]) -> datetime:
    if isinstance(date, datetime):
        return date

    return datetime.strptime(date, "%Y-%m-%d")


class Command(BaseCommand):
    help = "Update AHHS based on new household size data."
    required_csv_headers = {
        "Year",
        "AHHS",
        "ISO3",
        "Data source category",
        "Reference date",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file_path",
            type=str,
            help="Path to the CSV file containing the data.",
        )
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="AHHS year to be updated",
        )
        parser.add_argument(
            "--figure-update-mode",
            choices=FIGURE_UPDATE_MODES,
            required=True,
            help=(
                "How figures are updated: "
                f"'{FIGURE_UPDATE_MODE_NONE}' touches no figures; "
                f"'{FIGURE_UPDATE_MODE_NUMBERS}' updates household_size, total_figures and excerpt_idu; "
                f"'{FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE}' also appends the retroactive note to calculation_logic."
            ),
        )
        parser.add_argument(
            "--retroactive-update-date",
            type=str,
            help=(
                "Date (ISO format) when AHHS values were retroactively changed. "
                f"Required when --figure-update-mode={FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE}."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the full update inside a transaction, then roll back without committing.",
        )

    # NOTE: This function cannot be cached
    def iso3_to_household_sizes(self, year: int) -> typing.Dict[str, typing.Optional[HouseholdSize]]:
        household_sizes = HouseholdSize.objects.filter(year=year, is_active=True).select_related("country")
        return typing.cast(
            typing.Dict[str, typing.Optional[HouseholdSize]],
            CaseInsensitiveDict({size.country.iso3: size for size in household_sizes}),
        )

    @cached_property
    def iso3_to_country_id(self) -> CaseInsensitiveDict:
        """
        Map ISO3 country codes to Country objects.
        Returns:
            CaseInsensitiveDict: Keys are ISO3 codes, values are Country instances.
        """
        countries = Country.objects.filter(iso3__isnull=False)
        return CaseInsensitiveDict({iso3: _id for _id, iso3 in countries.values_list("id", "iso3")})

    @cached_property
    def admin_user(self) -> User:
        return HelixInternalBot().user

    @staticmethod
    def _normalize_for_comparison(value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return value

    @classmethod
    def household_size_unchanged(cls, existing: HouseholdSize, item: typing.Dict) -> bool:
        return all(
            cls._normalize_for_comparison(getattr(existing, field)) == cls._normalize_for_comparison(item.get(field))
            for field in HOUSEHOLD_SIZE_COMPARISON_FIELDS
        )

    def update_household_sizes(self, validated_data: typing.List[typing.Dict], tally: Counter) -> typing.List[typing.Dict]:
        changed_items = []
        for item in validated_data:
            existing_active = HouseholdSize.objects.filter(
                country=item["country"],
                year=item["year"],
                is_active=True,
            )
            # Only a single clean active record can be judged "unchanged"; dirty duplicates fall through to be replaced.
            if existing_active.count() == 1 and self.household_size_unchanged(existing_active.get(), item):
                tally["unchanged"] += 1
                self.stdout.write(f"AHHS for {item['country']} is unchanged. Skipping.")
                continue

            # NOTE: deactivating previous values
            updated_households = existing_active.update(is_active=False)
            if updated_households > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Deactivated {updated_households} previous AHHS items for {item['country']}.",
                    )
                )

            new_ahhs = HouseholdSize.objects.create(
                **item,
            )
            # NOTE: Because of updates to created_at/modified_at we haven't used bulk_create
            HouseholdSize.objects.filter(pk=new_ahhs.pk).update(
                created_at=item["created_at"],
                last_modified_by=item["last_modified_by"],
                modified_at=item["modified_at"],
            )
            tally["created"] += 1
            changed_items.append(item)
            self.stdout.write(self.style.SUCCESS(f"Created AHHS item for {item['country']}"))
        return changed_items

    def process_household_size_row(self, row: DataRow, year: int) -> typing.Optional[typing.Dict]:
        if row["Year"] != str(year):
            return None

        country_id = None
        if iso3 := row.get("ISO3"):
            country_id = self.iso3_to_country_id.get(iso3)

        created_at = format_date(datetime.today())

        modified_at = created_at
        if idmc_update_date := row.get("IDMC update date"):
            modified_at = format_date(idmc_update_date)

        # NOTE: For some regions we do not have permanent residence so AHHS can be zero
        size = row["AHHS"]
        if size is None or size == "":
            size = 0

        reference_year = datetime.strptime(row["Reference date"], "%Y-%m-%d").year
        gap_filling_method = calculate_gap_filling_method(int(row["Year"]), reference_year)

        return {
            # Data from csv
            "size": size,
            "year": row["Year"],
            "reference_date": row["Reference date"],
            "gap_filling_method": gap_filling_method,
            "country": country_id,
            "data_source_category": row["Data source category"],
            "source": row.get("Source", "No Data"),
            "source_link": row.get("Source link", ""),
            "notes": row.get("Notes"),
            # Additional metadata
            "created_by": self.admin_user.pk,
            "last_modified_by": self.admin_user.pk,
            "created_at": created_at,
            "modified_at": modified_at,
            "is_active": True,
        }

    def update_household_sizes_from_csv(self, file_path: str, year: int, tally: Counter) -> typing.List[typing.Dict]:
        with open(file_path, "r") as file:
            reader = csv.DictReader(file)

            csv_headers = set(reader.fieldnames or [])
            missing_headers = self.required_csv_headers.difference(csv_headers)
            if missing_headers:
                raise ValueError(f"Missing required headers in CSV: {', '.join(missing_headers)}")

            processed_rows = []
            total = 0

            for row in reader:
                if processed_row := self.process_household_size_row(typing.cast(DataRow, row), year):
                    total += 1
                    processed_rows.append(processed_row)

            if len(processed_rows) != total:
                self.stdout.write(self.style.NOTICE(f"Processed {len(processed_rows)} out of {total} AHHS items from CSV"))
            else:
                self.stdout.write(f"Processed {len(processed_rows)} out of {total} AHHS items from CSV")

            changed_items = []
            serializer = HouseholdSizeCliImportSerializer(data=processed_rows, many=True)
            if serializer.is_valid():
                changed_items = self.update_household_sizes(serializer.validated_data, tally)
            else:
                for i, errors in enumerate(serializer.errors):
                    if errors:
                        self.stdout.write(self.style.ERROR(f"---- Error in row {i + 1} ---- "))
                        self.stdout.write(self.style.ERROR(f"Row data: {processed_rows[i]}"))
                    for field, error in errors.items():
                        self.stdout.write(self.style.ERROR(f"'{field}': {error}"))
                raise Exception("Import failed")

            return changed_items

    def update_figure(
        self,
        bulk_mgr: BulkUpdateManager,
        figure: Figure,
        old_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        new_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        retroactive_update_date: typing.Optional[datetime],
        mode: str,
        tally: Counter,
    ):
        old_household_size = old_household_sizes.get(figure.country.iso3)
        if old_household_size is not None and figure.household_size != old_household_size.size:
            self.stdout.write(
                self.style.WARNING(
                    f"In figure <{figure.pk}>, household size does not match. "
                    f" Expected {figure.household_size} but found {old_household_size.size}. Skipping."
                )
            )
            tally["skipped"] += 1
            return

        old_household_size = figure.household_size
        new_household_size = new_household_sizes.get(figure.country.iso3)
        if new_household_size is None:
            self.stdout.write(
                self.style.WARNING(
                    f"In figure <{figure.pk}>, new household size not found for country {figure.country.iso3}. Skipping."
                )
            )
            tally["skipped"] += 1
            return

        if old_household_size == new_household_size.size:
            tally["unchanged"] += 1
            return

        if new_household_size.size == 0:
            tally["skipped"] += 1
            return

        self.stdout.write(
            f"In figure <{figure.pk}>, updating household size from {old_household_size} to {new_household_size.size}"
        )
        figure.household_size = new_household_size.size

        old_total_figures = figure.total_figures
        new_total_figures = int(round_half_up(figure.reported * Decimal(str(figure.household_size))))
        figure.total_figures = new_total_figures
        tally["changed"] += 1

        if old_total_figures != new_total_figures:
            self.stdout.write(
                f"In figure <{figure.pk}>, updating total figures from {old_total_figures} to {new_total_figures}"
            )
            if figure.excerpt_idu:
                # Match the figure value at a word boundary
                # We are adding a hack so that 1000 becomes 1,?0,?0,?0 and it matches any kind of comma separators
                excerpt_regex = re.compile("\\b" + ",?".join(list(str(old_total_figures))) + "\\b")
                new_excerpt_idu = re.sub(excerpt_regex, str(new_total_figures), figure.excerpt_idu)

                if figure.excerpt_idu == new_excerpt_idu:
                    self.stdout.write(
                        self.style.WARNING(f"In figure <{figure.pk}>, excerpt idu ({figure.excerpt_idu}) is unchanged")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"In figure <{figure.pk}>, excerpt idu ({figure.excerpt_idu}) is changed to ({new_excerpt_idu})"
                        )
                    )

                figure.excerpt_idu = new_excerpt_idu

            if mode == FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE:
                append_calculation_logic = (
                    f"On {retroactive_update_date.day} of {retroactive_update_date.strftime('%B')} "
                    f"{retroactive_update_date.year}, there was a retrospective update in AHHS; "
                    f"the value changed from {old_household_size} to {new_household_size.size} and "
                    f"the total figure changed from {old_total_figures} to {new_total_figures}. "
                    "Therefore, the text in the analysis may reflect old value."
                )
                if figure.calculation_logic:
                    figure.calculation_logic = f"{figure.calculation_logic}\n\n{append_calculation_logic}"
                else:
                    figure.calculation_logic = append_calculation_logic
                tally["note_appended"] += 1

        bulk_mgr.add(figure)

    def update_figures(
        self,
        year: int,
        old_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        new_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        filter_countries: typing.Set[str],
        retroactive_update_date: typing.Optional[datetime],
        mode: str,
        tally: Counter,
    ):
        update_fields = ["household_size", "total_figures", "excerpt_idu"]
        if mode == FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE:
            update_fields.append("calculation_logic")
        bulk_mgr = BulkUpdateManager(
            update_fields,
            chunk_size=1000,
        )

        figures = Figure.objects.filter(
            unit=Figure.UNIT.HOUSEHOLD,
            # NOTE: in the frontend we are using "start_date" to get household size
            start_date__year=year,
            country__in=filter_countries,
        )
        for figure in figures:
            self.update_figure(
                bulk_mgr,
                figure,
                old_household_sizes,
                new_household_sizes,
                retroactive_update_date,
                mode,
                tally,
            )

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f"Updated figures: {bulk_mgr.summary()}"))

    def print_summary(
        self,
        household_tally: Counter,
        figure_tally: typing.Optional[Counter],
        dry_run: bool,
    ):
        self.stdout.write(
            self.style.SUCCESS(
                f"AHHS: created {household_tally['created']}, unchanged {household_tally['unchanged']}"
            )
        )
        if figure_tally is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Figures: changed {figure_tally['changed']}, skipped {figure_tally['skipped']}, "
                    f"unchanged {figure_tally['unchanged']}, notes appended {figure_tally['note_appended']}"
                )
            )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: all changes rolled back; nothing was committed."))

    @transaction.atomic()
    def handle(self, *args, **kwargs):
        """
        Entry point for processing the CSV file to update Household Size.
        """
        csv_file_path = kwargs["csv_file_path"]
        year = kwargs["year"]
        mode = kwargs["figure_update_mode"]
        dry_run = kwargs["dry_run"]
        retroactive_update_date = kwargs["retroactive_update_date"]

        if mode == FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE and not retroactive_update_date:
            raise CommandError(
                f"--retroactive-update-date is required when --figure-update-mode={FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE}"
            )

        if not os.path.exists(csv_file_path):
            raise CommandError(f"CSV file path does not exist: {csv_file_path}")

        household_tally: Counter = Counter()
        old_household_sizes_map = self.iso3_to_household_sizes(year)

        changed_household_sizes = self.update_household_sizes_from_csv(csv_file_path, year, household_tally)

        figure_tally: typing.Optional[Counter] = None
        if mode != FIGURE_UPDATE_MODE_NONE:
            countries_set = set(x["country"].pk for x in changed_household_sizes)
            new_household_sizes_map = self.iso3_to_household_sizes(year)
            figure_tally = Counter()
            self.update_figures(
                year,
                old_household_sizes_map,
                new_household_sizes_map,
                countries_set,
                format_date(retroactive_update_date) if retroactive_update_date else None,
                mode,
                figure_tally,
            )

        self.print_summary(household_tally, figure_tally, dry_run)

        if dry_run:
            transaction.set_rollback(True)
