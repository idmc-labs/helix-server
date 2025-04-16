import csv
import datetime
import os
import typing
from decimal import Decimal
from functools import cached_property

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


def format_date(date: str) -> typing.Union[datetime.datetime, str]:
    try:
        return datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return date


class Command(BaseCommand):

    help = "Update AHHS based on new household size data."

    def add_arguments(self, parser):
        parser.add_argument("csv_file_path", type=str, help="Path to the CSV file containing the data.")
        parser.add_argument(
            "year",
            nargs="+",
            type=int,
            help="AHHS year to be updated",
        )

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
        return CaseInsensitiveDict({
            iso3: _id
            for _id, iso3 in countries.values_list('id', 'iso3')
        })

    @cached_property
    def admin_user(self) -> User:
        return HelixInternalBot().user

    def create_household_sizes(self, validated_data: typing.List[dict]):
        updated_count = 0
        for item in validated_data:
            # NOTE: deactivating previous values
            updated_households = HouseholdSize.objects.filter(
                country=item['country'],
                year=item['year'],
                is_active=True,
            ).update(is_active=False)
            updated_count += updated_households

            new_ahhs = HouseholdSize.objects.create(
                **item,
            )
            # NOTE: Because of this we haven't used bulk_create
            HouseholdSize.objects.filter(pk=new_ahhs.pk).update(
                created_at=item['created_at'],
                last_modified_by=item['last_modified_by'],
                modified_at=item['modified_at'],
            )
        self.stdout.write(self.style.SUCCESS(f"Created {len(validated_data)} AHHS items."))
        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} previous AHHS items as inactive."))

    def process_household_size_row(self, row: dict) -> typing.Optional[dict]:
        """
        Convert a CSV row into a dictionary suitable for serialization.
        Args:
            row (Dict[str, str]): The row from CSV file.
        Returns:
            Dict[str, any]: The processed row with country ID.
        """
        country_id = None
        if iso3 := row.get('ISO3'):
            country_id = self.iso3_to_country_id.get(iso3)

        extract_data = {
            'size': row['AHHS'],
            'data_source_category': row['Data source category'],
            'source': row['Source'],
            'source_link': row['Source link'],
        }
        if not all(extract_data.values()):
            self.stdout.write(self.style.NOTICE(f'Skipping due to empty dataset: {row}'))
            return

        created_at = format_date(row['Reference date'])
        modified_at = format_date(row['IDMC update date']) or created_at
        return {
            # Data from csv
            **extract_data,
            'country': country_id,
            'year': row['Year'],
            'notes': row['Notes'],
            # Additional metadata
            'created_by': self.admin_user.pk,
            'last_modified_by': self.admin_user.pk,
            'created_at': created_at,
            'modified_at': modified_at,
            'is_active': True,
        }

    def updates_household_sizes_from_csv(self, file_path):
        """
        Processes the CSV file and updates the database.
        """
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            processed_rows = []
            total = 0
            for row in reader:
                total += 1
                if processed_row := self.process_household_size_row(row):
                    processed_rows.append(processed_row)
            self.stdout.write(self.style.NOTICE(
                f"Processed {len(processed_rows)} out of {total} AHHS items from CSV"
            ))

            household_values = []

            serializer = HouseholdSizeCliImportSerializer(data=processed_rows, many=True)
            if serializer.is_valid():
                household_values = serializer.validated_data
                self.create_household_sizes(serializer.validated_data)
            else:
                for i, errors in enumerate(serializer.errors):
                    if errors:
                        self.stdout.write(self.style.ERROR(f"---- Error in row {i + 1} ---- "))
                        self.stdout.write(self.style.NOTICE(f"Row data: {processed_rows[i]}"))
                    for field, error in errors.items():
                        self.stdout.write(self.style.ERROR(f"'{field}': {error}"))
                raise Exception('Import failed')
            return household_values

    def update_figure_with_new_household_size(
        self,
        bulk_mgr: BulkUpdateManager,
        figure: Figure,
        old_household_sizes: CaseInsensitiveDict,
        new_household_sizes: CaseInsensitiveDict,
    ):
        """
        Updates the household size of a figure if it differs from the current size stored.
        Args:
            figure (Figure): The figure object to update.
        """

        old_household_size = old_household_sizes.get(figure.country.iso3)
        if old_household_size and figure.household_size != old_household_size.size:
            self.stdout.write(self.style.WARNING(
                f"In figure <{figure.pk}>, household size manually changed"
                f" from {old_household_size.size} to {figure.household_size}"
            ))
            return

        new_household_size = new_household_sizes.get(figure.country.iso3)
        if new_household_size is None:
            self.stdout.write(self.style.WARNING(f"Household size not found for country {figure.country.iso3}"))
            return

        if figure.household_size == new_household_size.size:
            self.stdout.write(self.style.NOTICE(
                f"In figure <{figure.pk}, household size has not changed {figure.household_size}"
            ))
            return

        self.stdout.write(self.style.NOTICE(
            f"In figure <{figure.pk}>, updating household size from {figure.household_size} to {new_household_size.size}"
        ))
        figure.household_size = new_household_size.size
        figure.total_figures = round_half_up(figure.reported * Decimal(str(figure.household_size)))
        bulk_mgr.add(figure)

    def update_figures(
        self,
        year: int,
        old_household_sizes: CaseInsensitiveDict,
        new_household_sizes: CaseInsensitiveDict,
        filter_countries: typing.Set[str],
    ):
        bulk_mgr = BulkUpdateManager(['household_size', 'total_figures'], chunk_size=1000)
        figures = Figure.objects.filter(
            unit=Figure.UNIT.HOUSEHOLD,
            # Year can be calculated from the end_date (for both flow and stock figures)
            end_date__year=year,
            country__in=filter_countries,
        )
        for figure in figures:
            self.update_figure_with_new_household_size(
                bulk_mgr,
                figure,
                old_household_sizes,
                new_household_sizes,
            )

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f'Updated figures: {bulk_mgr.summary()}'))

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

        old_household_sizes = self.iso3_to_household_sizes(year)
        household_sizes = self.updates_household_sizes_from_csv(csv_file_path)
        # FIXME: We may need to clear cache
        new_household_sizes = self.iso3_to_household_sizes(year)

        self.update_figures(year, old_household_sizes, new_household_sizes, set([x["country"].pk for x in household_sizes]))
