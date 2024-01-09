from django.db.models.query import QuerySet

from apps.country.models import HouseholdSize
from utils.factories import HouseholdSizeFactory, CountryFactory
from utils.tests import HelixTestCase

from apps.country.management.commands.clone_household_sizes import Command as CloneCommand


class TestHouseholdSizeClone(HelixTestCase):
    def setUp(self) -> None:
        self.countries = (
            self.country_1,
            self.country_2,
            self.country_3,
        ) = CountryFactory.create_batch(3)
        # Create some HouseholdSize
        for year in [2021, 2022, 2023]:
            for country in self.countries:
                HouseholdSizeFactory.create(year=year, country=country)
        self.command = CloneCommand()

    @staticmethod
    def serialize_household_size(items: QuerySet):
        return [
            {
                'id': item.id,
                'country': item.country_id,
                'year': item.year,
                'size': item.size,
            }
            for item in items
        ]

    def test_clone_command_error(self):
        existing_dataset = self.serialize_household_size(HouseholdSize.objects.all())
        # Run the command
        self.command.handle(source_year=2022, destination_year=2023)
        # Above command should return with success. Resulting in new AHHS
        new_dataset = self.serialize_household_size(HouseholdSize.objects.all())
        assert len(existing_dataset) == len(new_dataset)
        assert new_dataset == existing_dataset

    def test_clone_command_success(self):
        existing_dataset = self.serialize_household_size(HouseholdSize.objects.all())
        self.command.handle(source_year=2023, destination_year=2024)
        # Above command should return with success. Resulting in new AHHS
        new_dataset = self.serialize_household_size(HouseholdSize.objects.all())
        assert len(new_dataset) == len(existing_dataset) + 3
        assert new_dataset == [
            *existing_dataset,
            *self.serialize_household_size(
                HouseholdSize.objects.filter(year=2024)
            )
        ]
