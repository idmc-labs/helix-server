"""The reusable bulk-import management command base class."""

import typing

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework import serializers as drf_serializers

from apps.contrib.bulk_operations.tasks import generate_dummy_request
from apps.users.utils import HelixInternalBot

from .lookups import BaseLookup, ResolutionError
from .reader import read_rows
from .template import write_template
from .utils import DISPLAY_SEP, is_empty

User = get_user_model()


class BaseImportCommand(BaseCommand):
    """
    Reusable management command for bulk creating/updating model rows from an xlsx sheet,
    validated through DRF serializers, all-or-nothing within a single transaction.

    Subclasses set: model, create_serializer, update_serializer, lookups.
    """

    model = None
    create_serializer = None
    update_serializer = None
    lookups: typing.List[BaseLookup] = []

    DATA_SHEET = "Data"

    #: Case-insensitive cell text that explicitly clears a field on an update.
    #: A blank or whitespace-only cell leaves the field unchanged
    CLEAR_TOKEN = "<clear>"

    #: Global denylist: fields that must never be in importable columns
    #: even when a serializer uses ``fields = "__all__"`` and exposes them
    #: id is intentionally NOT excluded here: it is used to identify create/update action.
    EXCLUDED_FIELDS = frozenset(
        {
            "old_id",
            "version_id",
            "deleted_on",
            "created_at",
            "created_by",
            "modified_at",
            "last_modified_by",
        }
    )

    #: Local denylist: additional fields must not be in importable columns
    EXTRA_EXCLUDED_FIELDS: typing.FrozenSet[str] = frozenset()

    @property
    def excluded_fields(self) -> typing.FrozenSet[str]:
        return self.EXCLUDED_FIELDS | frozenset(self.EXTRA_EXCLUDED_FIELDS)

    # ----- argparse -----

    def add_arguments(self, parser):
        parser.add_argument("file_path", nargs="?", type=str, help="Path to the .xlsx file to import.")
        parser.add_argument("--user-email", type=str, help="Email of the user to attribute changes to.")
        parser.add_argument("--dry-run", action="store_true", help="Validate and save, then roll back.")
        parser.add_argument(
            "--make-template",
            dest="make_template",
            type=str,
            metavar="OUT_PATH",
            help="Write a blank import template to OUT_PATH and exit.",
        )

    # ----- configuration helpers -----

    @property
    def lookup_map(self) -> typing.Dict[str, BaseLookup]:
        return {lookup.field: lookup for lookup in self.lookups}

    @staticmethod
    def _writable_fields(serializer_cls) -> typing.List[str]:
        serializer = serializer_cls()
        return [name for name, field in serializer.fields.items() if not field.read_only]

    def import_columns(self) -> typing.List[str]:
        """
        Importable columns = writable fields of the create and update serializers,
        without EXCLUDED_FIELDS.
        """
        create_fields = self._writable_fields(self.create_serializer)
        update_fields = self._writable_fields(self.update_serializer)
        excluded = self.excluded_fields

        columns: typing.List[str] = []
        if "id" in update_fields:
            columns.append("id")
        for name in create_fields + update_fields:
            if name not in columns and name not in excluded:
                columns.append(name)
        return columns

    def required_create_columns(self) -> typing.Set[str]:
        """Importable columns that required by create serializer."""
        importable = set(self.import_columns())
        serializer = self.create_serializer()
        return {name for name, field in serializer.fields.items() if field.required and name in importable}

    _SCALAR_FIELDS = {
        # Scalar -> (type label, README note).
        "BooleanField": ("boolean", "true/false (also yes/no, on/off, 1/0)"),
        "NullBooleanField": ("boolean", "true/false (also yes/no, on/off, 1/0)"),
        "IntegerField": ("number", "whole number"),
        "FloatField": ("number", "decimal number"),
        "DecimalField": ("number", "decimal number"),
        "DateField": ("date", "YYYY-MM-DD"),
        "DateTimeField": ("datetime", "YYYY-MM-DDThh:mm:ssZ"),
    }

    def _scalar_field(self, column: str):
        create_fields = self.create_serializer().fields
        update_fields = self.update_serializer().fields
        return create_fields.get(column) or update_fields.get(column)

    def column_types(self) -> typing.Dict[str, str]:
        """Data-type label per importable column."""
        lookups = self.lookup_map
        types: typing.Dict[str, str] = {}
        for column in self.import_columns():
            if column in lookups:
                lookup = lookups[column]

                datatype = lookup.data_type()
                # Name/enum matching is case-sensitive; id-based references are not.
                types[column] = f"{datatype}, case-sensitive" if lookup.case_sensitive else datatype
            elif column == "id":
                types[column] = "number"
            else:
                field = self._scalar_field(column)
                TEXT_SCALAR_FIELD = ("text", "")
                types[column] = self._SCALAR_FIELDS.get(type(field).__name__, TEXT_SCALAR_FIELD)[0] if field else "text"
        return types

    def column_notes(self) -> typing.Dict[str, str]:
        """Per-column note, only for columns whose input format is non-obvious (else empty)."""
        lookups = self.lookup_map
        notes: typing.Dict[str, str] = {}
        for column in self.import_columns():
            if column in lookups:
                notes[column] = lookups[column].note()
            elif column == "id":
                notes[column] = ""
            else:
                field = self._scalar_field(column)
                TEXT_SCALAR_FIELD = ("text", "")
                notes[column] = self._SCALAR_FIELDS.get(type(field).__name__, TEXT_SCALAR_FIELD)[1] if field else ""
        return notes

    # ----- resolution + dispatch -----

    def _is_clear_token(self, value) -> bool:
        return isinstance(value, str) and value.strip().casefold() == self.CLEAR_TOKEN.casefold()

    def _scalar_clear_value(self, header):
        """Clear value for a scalar (no-lookup) field: "" for a non-null blank-allowed string, else None."""
        field = self._scalar_field(header)  # already exists on the class
        if isinstance(field, drf_serializers.CharField):
            if field.allow_null:
                return None
            if getattr(field, "allow_blank", False):
                return ""
        return None

    def prepare_row(self, raw_row: typing.Dict, request):
        """Resolve a raw row and build its serializer. Returns (serializer_or_none, is_update, row_errors)."""
        row_errors: typing.Dict[str, str] = {}
        data: typing.Dict = {}
        for header, value in raw_row.items():
            lookup = self.lookup_map.get(header)
            if is_empty(value):
                # Blank/whitespace leaves the field untouched (omitted from the payload).
                continue
            if self._is_clear_token(value):
                # Explicitly clear: nullable -> None, non-null blank-allowed string -> "", list fields -> [].
                data[header] = lookup.clear_value() if lookup is not None else self._scalar_clear_value(header)
                continue
            if lookup is None:
                data[header] = value
                continue
            try:
                data[header] = lookup.resolve(value)
            except ResolutionError as exc:
                row_errors[header] = str(exc)

        raw_id = raw_row.get("id")
        is_update = not is_empty(raw_id)

        serializer = None
        if is_update:
            instance = self.model.objects.filter(pk=raw_id).first()
            if instance is None:
                row_errors["id"] = f"no {self.model.__name__} found with id {raw_id}"
            else:
                serializer = self.update_serializer(instance=instance, data=data, partial=True, context={"request": request})
        else:
            data.pop("id", None)
            serializer = self.create_serializer(data=data, context={"request": request})

        if serializer is not None and not serializer.is_valid():
            for field, errors in serializer.errors.items():
                if field in row_errors:
                    # Keep the more specific lookup ResolutionError already recorded for this field.
                    continue
                error_list = errors if isinstance(errors, list) else [errors]
                row_errors[field] = DISPLAY_SEP.join(str(error) for error in error_list)

        return serializer, is_update, row_errors

    # ----- template metadata + checks -----

    #: Optional human label for the H1 title; defaults to the model's verbose_name.
    entity_name: typing.Optional[str] = None

    def template_title(self) -> str:
        name = self.entity_name or self.model._meta.verbose_name
        return f"{name.title()} Import Template"

    @staticmethod
    def _source_version() -> str:
        import os
        import subprocess

        release = os.environ.get("APP_RELEASE")
        if release:
            return release
        try:
            return subprocess.check_output(["git", "describe", "--always"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return "unknown"

    def template_metadata(self) -> typing.Dict[str, str]:
        from django.conf import settings
        from django.utils import timezone

        return {
            "Generated": timezone.now().isoformat(timespec="seconds"),
            "Source version": self._source_version(),
            "Environment": getattr(settings, "HELIX_ENVIRONMENT", None) or "unknown",
        }

    def template_warnings(self) -> typing.List[str]:
        """Non-fatal data-quality warnings for the generated template (duplicates, embedded separators)."""
        warnings: typing.List[str] = []
        for lookup in self.lookups:
            duplicates = lookup.duplicate_values()
            if duplicates:
                warnings.append(f"{lookup.field}: duplicate allowed value(s): {DISPLAY_SEP.join(duplicates)}")
            split = getattr(lookup, "split", None)
            if split:
                embedded = sorted({value for value in lookup.enumerate_values() if split in str(value)})
                if embedded:
                    warnings.append(
                        f"{lookup.field}: allowed value(s) contain the '{split}' separator "
                        f"(cannot be selected): {DISPLAY_SEP.join(embedded)}"
                    )
        return warnings

    # ----- attribution -----

    def resolve_user(self, user_email: typing.Optional[str]):
        if not user_email:
            return HelixInternalBot().user
        user = User.objects.filter(email=user_email).first()
        if user is None:
            raise CommandError(f"No user found with email {user_email}")
        return user

    # ----- entry point -----

    def handle(self, *args, **options):
        for lookup in self.lookups:
            lookup.reset()  # caches are per-invocation; never reuse across runs

        if options.get("make_template"):
            out_path = options["make_template"]
            for warning in self.template_warnings():
                self.stderr.write(self.style.WARNING(f"WARNING {warning}"))
            write_template(
                out_path,
                title=self.template_title(),
                metadata=self.template_metadata(),
                data_sheet=self.DATA_SHEET,
                columns=self.import_columns(),
                lookups=self.lookups,
                clear_token=self.CLEAR_TOKEN,
                required_columns=self.required_create_columns(),
                column_types=self.column_types(),
                column_notes=self.column_notes(),
            )
            self.stdout.write(self.style.SUCCESS(f"Template written to {out_path}"))
            return

        file_path = options.get("file_path")
        if not file_path:
            raise CommandError("Provide a file_path to import, or --make-template OUT_PATH.")

        user = self.resolve_user(options.get("user_email"))
        request = generate_dummy_request(user)
        rows = read_rows(file_path, data_sheet=self.DATA_SHEET, allowed_columns=self.import_columns())
        self.run_import(rows, request, dry_run=options.get("dry_run", False))

    @transaction.atomic
    def run_import(self, rows: typing.List[typing.Dict], request, dry_run: bool):
        errors: typing.List[typing.Tuple[int, str, str]] = []
        prepared: typing.List[typing.Tuple] = []

        # First pass: resolve + validate every row, collecting all errors (all-or-nothing).
        for index, raw_row in enumerate(rows, start=2):  # row 1 is the header
            serializer, is_update, row_errors = self.prepare_row(raw_row, request)
            if row_errors:
                for field, message in row_errors.items():
                    errors.append((index, field, message))
            else:
                prepared.append((serializer, is_update))

        if errors:
            self.stdout.write(self.style.ERROR(f"Import failed: {len(errors)} error(s); nothing committed."))
            for row_number, field, message in errors:
                self.stdout.write(self.style.ERROR(f"Row {row_number}: {field}: {message}"))
            raise CommandError("Import aborted due to validation errors.")

        # Second pass: persist.
        created = updated = 0
        for serializer, is_update in prepared:
            serializer.save()
            if is_update:
                updated += 1
            else:
                created += 1

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(f"DRY RUN: would create {created}, update {updated}; rolled back."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created {created}, updated {updated}."))
