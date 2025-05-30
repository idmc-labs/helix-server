import csv
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.entry.models import Figure
from helix.managers import BulkUpdateManager
from utils.common import round_half_up


class Command(BaseCommand):
    help = "Patch AHHS household size data."

    def add_arguments(self, parser):
        parser.add_argument("csv_file_path", type=str, help="Path to the CSV file containing the data.")

    def patch_figure_household_from_csv(self, file_path):
        change_in_reported_value_figures = []
        change_in_unit_figures = []
        figure_id_not_found = []
        no_change_in_household_figures = []
        patched_figure_ids = []

        bulk_mgr = BulkUpdateManager(["household_size", "total_figures"], chunk_size=1000)

        with open(file_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                fig_id = row["figure_id"]
                figure = Figure.objects.filter(id=fig_id).first()

                if not figure:
                    figure_id_not_found.append(fig_id)
                    continue

                if figure.unit != Figure.UNIT.HOUSEHOLD:
                    change_in_unit_figures.append(figure.id)
                    continue

                if figure.reported != int(row["figure_reported_value"]):
                    change_in_reported_value_figures.append(figure.id)
                    continue

                if figure.household_size == float(row["figure_household_size"]):
                    no_change_in_household_figures.append(figure.id)
                    continue

                bulk_mgr.add(
                    Figure(
                        id=row["figure_id"],
                        household_size=float(row["figure_household_size"]),
                        total_figures=round_half_up(
                            int(row["figure_reported_value"]) * Decimal(str(row["figure_household_size"]))
                        ),
                    ),
                )
                patched_figure_ids.append(row["figure_id"])
        bulk_mgr.done()

        if figure_id_not_found:
            self.stdout.write(self.style.ERROR(f"Figure id not found ids: {figure_id_not_found}"))

        if change_in_unit_figures:
            self.stdout.write(self.style.ERROR(f"Figure unit not household ids: {change_in_unit_figures}"))

        if change_in_reported_value_figures:
            self.stdout.write(self.style.ERROR(f"Change in reported value figure ids: {change_in_reported_value_figures}"))

        if no_change_in_household_figures:
            self.stdout.write(f"No change in household size figure ids: {no_change_in_household_figures}")

        self.stdout.write(self.style.SUCCESS(f"Bulk update summary: {bulk_mgr.summary()}"))
        self.stdout.write(f"IDs of figures patched: {patched_figure_ids}")

    @transaction.atomic()
    def handle(self, *args, **kwargs):
        csv_file_path = kwargs["csv_file_path"]
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file path does not exist: {csv_file_path}"))
            return

        self.patch_figure_household_from_csv(csv_file_path)
        self.stdout.write("AHHS data patched successfully.")
