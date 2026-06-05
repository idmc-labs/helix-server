import csv
import os
import re
import typing
from datetime import datetime
from decimal import Decimal
from functools import cached_property
from typing import Union

from django.core.management.base import BaseCommand
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


def calculate_gap_filling_method(year, reference_year):
    if reference_year == year:
        return HouseholdSize.GAP_FILLING_METHOD.EXACT
    if reference_year > year:
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
            "--retroactive-update-date",
            type=str,
            required=True,
            help="Date(ISO Format) when AHHS values was retroactively changed",
        )
        parser.add_argument(
            "--retroactive-notes-cutoff-year",
            type=int,
            required=True,
            help="Add note in calculation logic in figure before this year",
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

    def update_household_sizes(self, validated_data: typing.List[typing.Dict]):
        for item in validated_data:
            # NOTE: deactivating previous values
            updated_households = HouseholdSize.objects.filter(
                country=item["country"],
                year=item["year"],
                is_active=True,
            ).update(is_active=False)
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
            self.stdout.write(self.style.SUCCESS(f"Created AHHS item for {item['country']}"))

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

    def update_household_sizes_from_csv(self, file_path: str, year: int) -> tuple:
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

            household_values = []
            serializer = HouseholdSizeCliImportSerializer(data=processed_rows, many=True)
            if serializer.is_valid():
                household_values = serializer.validated_data
                self.update_household_sizes(serializer.validated_data)
            else:
                for i, errors in enumerate(serializer.errors):
                    if errors:
                        self.stdout.write(self.style.ERROR(f"---- Error in row {i + 1} ---- "))
                        self.stdout.write(self.style.ERROR(f"Row data: {processed_rows[i]}"))
                    for field, error in errors.items():
                        self.stdout.write(self.style.ERROR(f"'{field}': {error}"))
                raise Exception("Import failed")

            return household_values

    def update_figure(
        self,
        bulk_mgr: BulkUpdateManager,
        figure: Figure,
        old_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        new_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        retroactive_update_date: datetime,
        retroactive_notes_cutoff_year: int,
    ):
        old_household_size = old_household_sizes.get(figure.country.iso3)
        if old_household_size is not None and figure.household_size != old_household_size.size:
            self.stdout.write(
                self.style.WARNING(
                    f"In figure <{figure.pk}>, household size does not match. "
                    f" Expected {figure.household_size} but found {old_household_size.size}. Skipping."
                )
            )
            return

        old_household_size = figure.household_size
        new_household_size = new_household_sizes.get(figure.country.iso3)
        if new_household_size is None:
            self.stdout.write(
                self.style.WARNING(
                    f"In figure <{figure.pk}>, new household size not found for country {figure.country.iso3}. Skipping."
                )
            )
            return

        if old_household_size == new_household_size.size:
            return

        if new_household_size.size == 0:
            return

        self.stdout.write(
            f"In figure <{figure.pk}>, updating household size from {old_household_size} to {new_household_size.size}"
        )
        figure.household_size = new_household_size.size

        old_total_figures = figure.total_figures
        new_total_figures = int(round_half_up(figure.reported * Decimal(str(figure.household_size))))
        figure.total_figures = new_total_figures

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

            figure_year = figure.gidd_year()
            if figure_year and figure_year < retroactive_notes_cutoff_year:
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

        bulk_mgr.add(figure)

    def update_figures(
        self,
        year: int,
        old_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        new_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        filter_countries: typing.Set[str],
        retroactive_update_date: datetime,
        retroactive_notes_cutoff_year: int,
    ):
        bulk_mgr = BulkUpdateManager(
            ["household_size", "total_figures", "excerpt_idu", "calculation_logic"],
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
                retroactive_notes_cutoff_year,
            )

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f"Updated figures: {bulk_mgr.summary()}"))

    @transaction.atomic()
    def handle(self, *args, **kwargs):
        """
        Entry point for processing the CSV file to update Household Size.
        """
        csv_file_path = kwargs["csv_file_path"]
        year = kwargs["year"]

        retroactive_update_date = kwargs["retroactive_update_date"]
        retroactive_notes_cutoff_year = kwargs["retroactive_notes_cutoff_year"]

        # FIXME: these assertions are not required
        assert year is not None, "year is required"
        assert retroactive_update_date is not None, "retroactive_update_date is required"
        assert retroactive_notes_cutoff_year is not None, "retroactive_notes_cutoff_year is required"

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file path does not exist: {csv_file_path}"))
            return

        old_household_sizes_map = self.iso3_to_household_sizes(year)

        new_household_sizes = self.update_household_sizes_from_csv(csv_file_path, year)

        countries_set = set([x["country"].pk for x in new_household_sizes])

        # FIXME: We may need to clear cache
        new_household_sizes_map = self.iso3_to_household_sizes(year)

        self.update_figures(
            year,
            old_household_sizes_map,
            new_household_sizes_map,
            countries_set,
            format_date(retroactive_update_date),
            retroactive_notes_cutoff_year,
        )
