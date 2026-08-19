import typing
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.event.constants import CONFLICT_TYPES, DISASTERS, OTHER_SUB_TYPES
from apps.event.models import (
    DisasterCategory,
    DisasterSubCategory,
    DisasterSubType,
    DisasterType,
    OtherSubType,
    Violence,
    ViolenceSubType,
)

Tally = typing.Dict[str, Counter]


class Command(BaseCommand):
    help = "Initialize or update event types."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and save, then roll back without committing.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        tally: Tally = {}
        self.create_other_sub_types(tally)
        self.create_violence_types(tally)
        self.create_disaster_types(tally)
        self.print_tally(tally, dry_run)

        if dry_run:
            transaction.set_rollback(True)

    def sync(self, tally: Tally, label: str, model, lookup: dict, defaults: dict):
        """
        Create the row or update it only when a default field actually differs.
        Records the outcome (created/updated/unchanged) under ``label`` and returns the row.
        """
        instance, created = model.objects.get_or_create(**lookup, defaults=defaults)
        if created:
            status = "created"
        else:
            changed_fields = [field for field, value in defaults.items() if getattr(instance, field) != value]
            if changed_fields:
                for field in changed_fields:
                    setattr(instance, field, defaults[field])
                instance.save(update_fields=changed_fields)
                status = "updated"
            else:
                status = "unchanged"
        tally.setdefault(label, Counter())[status] += 1
        return instance

    # other sub types
    def create_other_sub_types(self, tally: Tally):
        for sub_type in OTHER_SUB_TYPES:
            self.sync(
                tally,
                "Other sub types",
                OtherSubType,
                lookup={"name__iexact": sub_type.name},
                defaults={"name": sub_type.name, "idu_name": sub_type.idu_name},
            )

    # violence
    def create_violence_types(self, tally: Tally):
        for violence_name, sub_types in CONFLICT_TYPES.items():
            violence = self.sync(
                tally,
                "Violence",
                Violence,
                lookup={"name__iexact": violence_name},
                defaults={"name": violence_name},
            )

            for sub_type in sub_types:
                self.sync(
                    tally,
                    "Violence sub types",
                    ViolenceSubType,
                    lookup={"name__iexact": sub_type.name, "violence": violence},
                    defaults={"name": sub_type.name, "idu_name": sub_type.idu_name},
                )

    # disasters
    def create_disaster_types(self, tally: Tally):
        for cat_name, subcats in DISASTERS.items():
            category = self.sync(
                tally,
                "Hazard categories",
                DisasterCategory,
                lookup={"name__iexact": cat_name},
                defaults={"name": cat_name},
            )

            for subcat_name, types in subcats.items():
                sub_category = self.sync(
                    tally,
                    "Hazard sub categories",
                    DisasterSubCategory,
                    lookup={"name__iexact": subcat_name, "category": category},
                    defaults={"name": subcat_name},
                )

                for dtype_name, dsubtypes in types.items():
                    disaster_type = self.sync(
                        tally,
                        "Hazard types",
                        DisasterType,
                        lookup={"name__iexact": dtype_name, "disaster_sub_category": sub_category},
                        defaults={"name": dtype_name},
                    )

                    for dsubtype in dsubtypes:
                        self.sync(
                            tally,
                            "Hazard sub types",
                            DisasterSubType,
                            lookup={"name__iexact": dsubtype.name, "type": disaster_type},
                            defaults={"name": dsubtype.name, "idu_name": dsubtype.idu_name},
                        )

    def print_tally(self, tally: Tally, dry_run: bool):
        total: Counter = Counter()
        for label, counter in tally.items():
            total.update(counter)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{label}: created {counter['created']}, updated {counter['updated']}, unchanged {counter['unchanged']}"
                )
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would create {total['created']}, update {total['updated']}; "
                    f"{total['unchanged']} unchanged; rolled back."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Total: created {total['created']}, updated {total['updated']}, unchanged {total['unchanged']}."
                )
            )
