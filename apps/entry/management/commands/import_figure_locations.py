import typing

from apps.contrib.management.base import (
    BaseImportCommand,
    EnumLookup,
)
from apps.entry.models import FigureLocation
from apps.entry.serializers import FigureLocationSerializer


class Command(BaseImportCommand):
    help = (
        "Bulk update existing figure locations from an .xlsx sheet to backfill "
        "p-code fields. Use --make-template to generate a blank template. "
        "This importer only updates existing rows (matched by id); it never creates."
    )

    model = FigureLocation
    update_serializer = FigureLocationSerializer
    update_only = True

    # Backfill scope: only id (to match the row) plus the p-code columns are
    # importable, so an operator cannot accidentally overwrite geocoding fields.
    # Allowlist, not denylist: any other (incl. future) model field is excluded.
    IMPORT_FIELDS = frozenset({"id", "pcode", "pcode_source", "pcode_accuracy"})

    # pcode_source is free text (no lookup); only pcode_accuracy is an enum.
    lookups = [
        EnumLookup("pcode_accuracy", FigureLocation.PCODE_ACCURACY),
    ]

    @property
    def excluded_fields(self) -> typing.FrozenSet[str]:
        all_fields = set(self.update_serializer().fields)
        return super().excluded_fields | frozenset(all_fields - self.IMPORT_FIELDS)
