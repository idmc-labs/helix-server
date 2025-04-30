import csv
import logging
import os
import typing
from functools import cached_property

from django.core.management.base import BaseCommand
from django.db import transaction
from requests.structures import CaseInsensitiveDict

from apps.country.models import Country, Crisis
from apps.gidd.models import IdpsSaddEstimate
from apps.gidd.serializers import IdpsSaddEstimateSerializer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update idps sadd estimates"

    @cached_property
    def iso3_to_country(self) -> typing.Dict[str, Country]:
        """
        Creates a dictionary mapping ISO3 country codes to country data, with error handling and optimized fetching.

        Returns:
            Dict[str, CountryDataType]: A case-insensitive dictionary where keys are ISO3 codes and values are country data.
        """
        countries = Country.objects.filter(iso3__isnull=False)
        return CaseInsensitiveDict({country.iso3: country for country in countries})

    def add_arguments(self, parser):
        parser.add_argument("csv_file_path", type=str, help="Path to the CSV file containing the data.")

    @classmethod
    def map_cause(cls, cause_string: str) -> int:
        """
        Maps a cause string to its corresponding enum value using the Crisis.CRISIS_TYPE enum.
        """
        if cause_string == Crisis.CRISIS_TYPE.CONFLICT.label:
            return Crisis.CRISIS_TYPE.CONFLICT.value
        elif cause_string == Crisis.CRISIS_TYPE.DISASTER.label:
            return Crisis.CRISIS_TYPE.DISASTER.value

    @transaction.atomic()
    def handle(self, *args, **kwargs):
        """
        Handles the command execution.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        csv_file_path = kwargs["csv_file_path"]
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file path does not exist: {csv_file_path}")
            return
        try:
            self.process_file(csv_file_path)
            logger.info("IDPS SADD estimates updated successfully.")
        except FileNotFoundError:
            logger.error(f"CSV file at {csv_file_path} not found.")
        except Exception:
            logger.error("Failed to update IDPS SADD estimates:", exc_info=True)

    def process_file(self, file_path):
        """
        Processes the CSV file and updates IDPS SADD estimates.

        Args:
            file_path (str): The path to the CSV file.
        """
        with open(file_path, "r") as file:
            reader = csv.DictReader(file)
            processed_rows = []
            for row in reader:
                processed_rows.append(self.process_row(row))
            serializer = IdpsSaddEstimateSerializer(data=processed_rows, many=True)
            if serializer.is_valid():
                self.create_estimates(serializer.validated_data)
            else:
                for i, errors in enumerate(serializer.errors):
                    for field, error in errors.items():
                        logger.error(f"Error in row {i + 1}, column '{field}': {error}. Row data: {processed_rows[i]}")

    def process_row(self, row: dict) -> dict:
        """
        Processes a single row of CSV data, ensuring it contains necessary ISO3 code and
        retrieves corresponding country data.

        Args:
            row (dict): A dictionary representing a single row of CSV data.

        Returns:
            dict: The updated row with additional country ID and name based on the ISO3 code.

        Raises:
            ValueError: If the 'iso3' key is missing in the row.
            LookupError: If no country data is found for the provided ISO3 code.
        """
        iso3 = row.get("iso3")
        country = self.iso3_to_country.get(iso3)
        return {**row, "country": country.id, "cause": self.map_cause(row.get("cause"))}

    def create_estimates(self, validated_data: typing.List[dict]):
        """
        Within a database transaction, it deletes all existing IdpsSaddEstimate records and then
        bulk creates new records from the validated CSV data.

        Args:
            validated_data (list): A list of validated data dictionaries to be saved to the database.
        """
        IdpsSaddEstimate.objects.all().delete()
        IdpsSaddEstimate.objects.bulk_create([IdpsSaddEstimate(**item) for item in validated_data])
        logger.info(f"Processed {len(validated_data)} new entries.")
