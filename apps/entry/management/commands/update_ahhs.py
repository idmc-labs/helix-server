import csv
import datetime
import os
import re
import typing
from decimal import Decimal
from functools import cached_property

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, OuterRef
from requests.structures import CaseInsensitiveDict

from apps.country.models import Country, HouseholdSize
from apps.country.serializers import HouseholdSizeCliImportSerializer
from apps.entry.models import Figure
from apps.report.models import Report
from apps.users.models import User
from apps.users.utils import HelixInternalBot
from helix.managers import BulkUpdateManager
from utils.common import round_half_up


def format_date(date: str) -> typing.Union[datetime.datetime, str]:
    try:
        return datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return date


class Command(BaseCommand):
    help = "Update AHHS based on new household size data."
    required_csv_headers = {
        "Year",
        "AHHS",
        "Data source category",
        "Source",
        "Source link",
        "Notes",
        "ISO3",
        "Reference date",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file_path",
            type=str,
            help="Path to the CSV file containing the data.",
        )
        parser.add_argument(
            "year",
            type=int,
            help="AHHS year to be updated",
        )

    # NOTE: This function cannot be cached
    def iso3_to_household_sizes(self, year: int) -> CaseInsensitiveDict:
        """
        Retrieves active household sizes for certain year, mapped by their respective countries.
        Returns:
            CaseInsensitiveDict: A dictionary with Country instances as keys and HouseholdSize instances as values.
        """
        household_sizes = HouseholdSize.objects.filter(year=year, is_active=True).select_related("country")
        return CaseInsensitiveDict({size.country.iso3: size for size in household_sizes})

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

    def update_household_sizes(self, validated_data: typing.List[dict]):
        updated_count = 0
        for item in validated_data:
            # NOTE: deactivating previous values
            updated_households = HouseholdSize.objects.filter(
                country=item["country"],
                year=item["year"],
                is_active=True,
            ).update(is_active=False)
            updated_count += updated_households

            new_ahhs = HouseholdSize.objects.create(
                **item,
            )
            # NOTE: Because of this we haven't used bulk_create
            HouseholdSize.objects.filter(pk=new_ahhs.pk).update(
                created_at=item["created_at"],
                last_modified_by=item["last_modified_by"],
                modified_at=item["modified_at"],
            )
        self.stdout.write(self.style.SUCCESS(f"Deactivated {updated_count} previous AHHS items."))
        self.stdout.write(self.style.SUCCESS(f"Created {len(validated_data)} AHHS items."))

    def process_household_size_row(self, row: dict, year: int) -> typing.Optional[dict]:
        """
        Convert a CSV row into a dictionary suitable for serialization.
        Args:
            row (Dict[str, str]): The row from CSV file.
        Returns:
            Dict[str, any]: The processed row with country ID.
        """
        if row["Year"] != str(year):
            return None

        extract_data = {
            "size": row["AHHS"],
            "data_source_category": row["Data source category"],
            "source": row["Source"] or "No Data",
            "source_link": row["Source link"],
        }
        if not all(extract_data.values()):
            self.stdout.write(self.style.WARNING(f"Skipping due to empty dataset: {row}"))
            return None

        country_id = None
        if iso3 := row.get("ISO3"):
            country_id = self.iso3_to_country_id.get(iso3)

        created_at = format_date(row["Reference date"])
        modified_at = format_date(row["IDMC update date"]) if row.get("IDMC update date") else created_at
        return {
            # Data from csv
            **extract_data,
            "country": country_id,
            "year": row["Year"],
            "notes": row["Notes"],
            # Additional metadata
            "created_by": self.admin_user.pk,
            "last_modified_by": self.admin_user.pk,
            "created_at": created_at,
            "modified_at": modified_at,
            "is_active": True,
        }

    def update_household_sizes_from_csv(self, file_path: str, year: int) -> tuple:
        """
        Processes the CSV file and updates the database.
        """
        with open(file_path, "r") as file:
            reader = csv.DictReader(file)
            csv_headers = set(reader.fieldnames or [])

            missing_headers = self.required_csv_headers.difference(csv_headers)
            if missing_headers:
                raise ValueError(f"Missing required columns in CSV: {', '.join(missing_headers)}")

            processed_rows = []
            missing_ahhs_countries = []
            total = 0
            for row in reader:
                total += 1
                if processed_row := self.process_household_size_row(row, year):
                    size = processed_row.get("size")
                    if size is None or size == "":
                        processed_row["size"] = 0
                        missing_ahhs_countries.append(processed_row["country"])
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
            return household_values, missing_ahhs_countries

    def update_figure(
        self,
        bulk_mgr: BulkUpdateManager,
        figure: Figure,
        old_household_sizes: CaseInsensitiveDict,
        new_household_sizes: CaseInsensitiveDict,
        dt: datetime.datetime,
    ):
        """
        Updates the household size of a figure if it differs from the current size stored.
        Args:
            figure (Figure): The figure object to update.
        """

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
            self.stdout.write(f"In figure <{figure.pk}>, household size has not changed {old_household_size}.")
            return

        self.stdout.write(
            f"In figure <{figure.pk}>, updating household size from {old_household_size} to {new_household_size.size}"
        )
        figure.household_size = new_household_size.size

        old_total_figures = figure.total_figures
        new_total_figures = int(round_half_up(figure.reported * Decimal(str(figure.household_size))))
        if old_total_figures == new_total_figures:
            self.stdout.write(f"In figure <{figure.pk}>, total figures has not changed {old_total_figures}")
        else:
            self.stdout.write(
                f"In figure <{figure.pk}>, updating total figures from {old_total_figures} to {new_total_figures}"
            )
            if figure.excerpt_idu:
                # Match the figure value at a word boundary
                # We are adding a hack so that 1000 becomes 1,?0,?0,?0 and it matches any kind of comma separators
                excerpt_regex = re.compile("\\b" + ",?".join(list(str(old_total_figures))) + "\\b")
                new_excerpt_idu = re.sub(excerpt_regex, str(new_total_figures), figure.excerpt_idu)
                self.stdout.write(f"Old excerpt idu ({figure.excerpt_idu}) is changed to ({new_excerpt_idu})")
                figure.excerpt_idu = new_excerpt_idu

        figure.total_figures = new_total_figures

        if figure.has_old_report:  # type: ignore an annotation
            append_calculation_logic = (
                f"On {dt.day} of {dt.strftime('%B')} {dt.year}, there was a retrospective update in AHHS; "
                f"The household size changed from {old_household_size} to {figure.household_size}, "
                f"and the total figure changed from {old_total_figures} to {figure.total_figures}. "
                "Therefore, the text in the analysis may reflect old value."
            )
            self.stdout.write(
                f"Appending ({append_calculation_logic}) to 'Analysis, Caveats and Calculation Logic' field in report"
            )

            figure.calculation_logic = f"{figure.calculation_logic}\n {append_calculation_logic}"

        bulk_mgr.add(figure)

    def update_figures(
        self,
        year: int,
        old_household_sizes: CaseInsensitiveDict,
        new_household_sizes: CaseInsensitiveDict,
        filter_countries: typing.Set[str],
    ):
        bulk_mgr = BulkUpdateManager([
            "household_size", "total_figures", "excerpt_idu", "calculation_logic"], chunk_size=1000
        )

        current_datetime = datetime.datetime.now()
        # Prevent queries inside the loop
        old_reports = Report.objects.filter(
            figures=OuterRef("pk"),
            gidd_report_year__lt=current_datetime.year,
        )

        figures = Figure.objects.filter(
            unit=Figure.UNIT.HOUSEHOLD,
            # Year can be calculated from the end_date (for both flow and stock figures)
            end_date__year=year,
            country__in=filter_countries,
        ).annotate(has_old_report=Exists(old_reports))
        for figure in figures:
            self.update_figure(
                bulk_mgr,
                figure,
                old_household_sizes,
                new_household_sizes,
                # The command can finish execution next year
                current_datetime,
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
        assert year is not None, "Year is required"
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file path does not exist: {csv_file_path}"))
            return

        old_household_sizes_map = self.iso3_to_household_sizes(year)

        new_household_sizes, skip_countries = self.update_household_sizes_from_csv(csv_file_path, year)

        # We don't update figures with missing AHHS in the CSV.
        countries_set = set([x["country"].pk for x in new_household_sizes if x["country"] not in skip_countries])

        # FIXME: We may need to clear cache
        new_household_sizes_map = self.iso3_to_household_sizes(year)

        self.update_figures(
            year,
            old_household_sizes_map,
            new_household_sizes_map,
            countries_set,
        )
