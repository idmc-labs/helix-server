"""The reusable bulk-import management command base class."""

import datetime
import enum
import typing
from contextlib import contextmanager

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


class PreparedRow(typing.NamedTuple):
    """One resolved sheet row, ready to save or to report on."""

    serializer: typing.Any
    is_update: bool
    errors: typing.Dict[str, str]
    #: Cells the operator filled that the serializer emptied.
    ignored_cells: typing.List[str]


class BaseImportCommand(BaseCommand):
    """
    Reusable management command for bulk creating/updating model rows from an xlsx sheet,
    validated through DRF serializers, all-or-nothing within a single transaction.

    Subclasses set: model, create_serializer, update_serializer, lookups.

    Set ``update_only = True`` for importers that only patch existing rows
    (e.g. backfills): a row with no match key is then rejected instead of
    creating a row, and ``create_serializer`` may be left unset.
    """

    model = None
    create_serializer = None
    update_serializer = None
    lookups: typing.List[BaseLookup] = []

    #: When True, rows without a match key are rejected (no create path). The
    #: template and column derivation fall back to ``update_serializer``.
    update_only = False

    #: Ordered ``(sheet column, model field)`` pairs an existing row may be named by. A row must
    #: supply exactly one of them; keys identify a row and are never written to it. Override to
    #: offer a second way in, e.g. ``(("id", "pk"), ("uuid", "uuid"))``.
    match_columns: typing.Tuple[typing.Tuple[str, str], ...] = (("id", "pk"),)

    DATA_SHEET = "Data"

    #: Case-insensitive cell text that explicitly clears a field on an update.
    #: A blank or whitespace-only cell leaves the field unchanged
    CLEAR_TOKEN = "<clear>"

    #: A cell cannot hold a list, so a list column's cell is split on this separator and each
    #: part is left to the serializer's child field to coerce and report on.
    LIST_SEP = ";"

    #: Longest value rendered into a changelog line before it is cut.
    CHANGELOG_VALUE_CHARS = 120

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
        create_fields = [] if self.update_only else self._writable_fields(self.create_serializer)
        update_fields = self._writable_fields(self.update_serializer)
        excluded = self.excluded_fields

        # Match keys lead, so the columns naming a row sit together at the front of the sheet.
        columns: typing.List[str] = [column for column, _ in self.match_columns]
        for name in create_fields + update_fields:
            if name not in columns and name not in excluded:
                columns.append(name)
        return columns

    @property
    def match_column_names(self) -> typing.Tuple[str, ...]:
        return tuple(column for column, _ in self.match_columns)

    def required_create_columns(self) -> typing.Set[str]:
        """
        Importable columns an operator must supply.

        With one match key that key is required outright. With several a row needs exactly one of
        them, so none is required on its own and the template says so in their notes instead.
        """
        importable = set(self.import_columns())
        if self.update_only:
            if len(self.match_columns) == 1:
                return set(self.match_column_names) & importable
            return set()
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
        update_fields = self.update_serializer().fields
        if self.update_only:
            return update_fields.get(column)
        create_fields = self.create_serializer().fields
        return create_fields.get(column) or update_fields.get(column)

    def _child_field(self, column: str):
        """The child field of a list column, or None when the column is not a list."""
        field = self._scalar_field(column)
        if isinstance(field, drf_serializers.ListField):
            return field.child
        return None

    def _narrow_cell(self, column: str, value):
        """
        A spreadsheet has no date type distinct from datetime, so openpyxl hands back a datetime
        for any date-formatted cell. A DateField column takes its date part; a DateTimeField keeps
        the whole value.
        """
        if isinstance(value, datetime.datetime) and isinstance(self._scalar_field(column), drf_serializers.DateField):
            return value.date()
        return value

    def _split_list_value(self, column: str, value):
        """Split a delimited cell for a list column; any other column's value passes through."""
        if self._child_field(column) is None:
            return value
        return [part.strip() for part in str(value).split(self.LIST_SEP) if part.strip()]

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
            elif column in self.match_column_names:
                types[column] = "number" if column == "id" else "text"
            else:
                child = self._child_field(column)
                field = self._scalar_field(column) if child is None else child
                TEXT_SCALAR_FIELD = ("text", "")
                label = self._SCALAR_FIELDS.get(type(field).__name__, TEXT_SCALAR_FIELD)[0] if field else "text"
                types[column] = f"{label} list" if child is not None else label
        return types

    def column_notes(self) -> typing.Dict[str, str]:
        """Per-column note, only for columns whose input format is non-obvious (else empty)."""
        lookups = self.lookup_map
        notes: typing.Dict[str, str] = {}
        for column in self.import_columns():
            if column in lookups:
                notes[column] = lookups[column].note()
            elif column in self.match_column_names:
                notes[column] = (
                    f"identifies the row; supply exactly one of {DISPLAY_SEP.join(self.match_column_names)}"
                    if len(self.match_columns) > 1
                    else ""
                )
            else:
                child = self._child_field(column)
                field = self._scalar_field(column) if child is None else child
                TEXT_SCALAR_FIELD = ("text", "")
                note = self._SCALAR_FIELDS.get(type(field).__name__, TEXT_SCALAR_FIELD)[1] if field else ""
                if child is not None:
                    note = f"{note} each, separated by '{self.LIST_SEP}'" if note else f"separated by '{self.LIST_SEP}'"
                notes[column] = note
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

    def serializer_context(self, request) -> typing.Dict:
        """
        Context handed to every row's serializer. Subclasses extend it when their serializer
        needs more than the request (e.g. a figure's bulk manager).
        """
        return {"request": request}

    def resolve_row(self, column: str, field: str, key):
        """
        Find the single row `key` names. Returns (instance, error_message); exactly one is set.

        Two rows are fetched rather than one because a match field is not necessarily unique —
        ``Figure.uuid`` carries whatever uuid an external import supplied and lost its unique
        constraint in 2021. An ambiguous key names both candidates instead of picking one.
        """
        queryset = self.model.objects.filter(**{field: key})
        matches = list(queryset[:2])
        if not matches:
            return None, f"no {self.model.__name__} found with {column} {key}"
        if len(matches) > 1:
            # Only reached on an ambiguous key, so naming every candidate is worth one more query.
            ids = ", ".join(str(pk) for pk in queryset.values_list("pk", flat=True))
            return None, (f"{column} {key} matches more than one {self.model.__name__} ({ids}); cannot tell which to edit")
        return matches[0], None

    def prepare_row(self, raw_row: typing.Dict, request):
        """Resolve a raw row and build its serializer. Returns (serializer_or_none, is_update, row_errors)."""
        row_errors: typing.Dict[str, str] = {}
        data: typing.Dict = {}
        cleared: typing.Set[str] = set()
        for header, value in raw_row.items():
            lookup = self.lookup_map.get(header)
            if is_empty(value):
                # Blank/whitespace leaves the field untouched (omitted from the payload).
                continue
            if self._is_clear_token(value):
                # Explicitly clear: nullable -> None, non-null blank-allowed string -> "",
                # a lookup's own list fields -> [].
                data[header] = lookup.clear_value() if lookup is not None else self._scalar_clear_value(header)
                cleared.add(header)
                continue
            if lookup is None:
                data[header] = self._split_list_value(header, self._narrow_cell(header, value))
                continue
            try:
                data[header] = lookup.resolve(value)
            except ResolutionError as exc:
                row_errors[header] = str(exc)

        # A key names a row; it is never written to it, so no key reaches the serializer payload.
        for column in self.match_column_names:
            data.pop(column, None)

        supplied = [(column, field) for column, field in self.match_columns if not is_empty(raw_row.get(column))]
        names = DISPLAY_SEP.join(self.match_column_names)
        is_update = bool(supplied)

        context = self.serializer_context(request)
        serializer = None
        if len(supplied) > 1:
            row_errors[supplied[0][0]] = f"exactly one of {names} is required; {len(supplied)} given"
        elif is_update:
            column, field = supplied[0]
            key = raw_row.get(column)
            instance, error = self.resolve_row(column, field, key)
            if error:
                row_errors[column] = error
            else:
                # The resolved pk, not the cell: a key written as text or as a float would
                # otherwise reach the serializer in whatever shape the sheet stored it.
                data["id"] = instance.pk
                serializer = self.update_serializer(instance=instance, data=data, partial=True, context=context)
        elif self.update_only:
            row_errors[self.match_column_names[0]] = (
                f"exactly one of {names} is required; none given. "
                f"This importer only updates existing {self.model.__name__} rows"
            )
        else:
            serializer = self.create_serializer(data=data, context=context)

        if serializer is not None and not serializer.is_valid():
            for field, errors in serializer.errors.items():
                if field in row_errors:
                    # Keep the more specific lookup ResolutionError already recorded for this field.
                    continue
                error_list = errors if isinstance(errors, list) else [errors]
                row_errors[field] = DISPLAY_SEP.join(str(error) for error in error_list)

        ignored = self.overridden_cells(serializer, raw_row, cleared) if not row_errors else []
        return PreparedRow(serializer, is_update, row_errors, ignored)

    #: Values a serializer leaves behind when it rejects a supplied cell.
    _EMPTIED = (None, [], "")

    def overridden_cells(self, serializer, raw_row: typing.Dict, cleared: typing.Set[str]) -> typing.List[str]:
        """
        Cells the operator filled that the serializer then emptied, so the sheet asked for
        something the row will not get.

        The comparison is against what survived validation, not against the raw cell: the payload
        is type-coerced on the way in, so a direct comparison would flag every cell. Only a cell
        emptied or dropped is reported - an override that swapped one value for another would not
        be seen, and no serializer here does that. Cells cleared on purpose are not overrides.
        """
        if serializer is None or not hasattr(serializer, "_validated_data"):
            return []
        validated = serializer.validated_data
        ignored = []
        for header in self.import_columns():
            if header in cleared or header in self.match_column_names:
                continue
            if is_empty(raw_row.get(header)):
                continue
            if header not in validated or validated[header] in self._EMPTIED:
                ignored.append(f"{header}={raw_row.get(header)}")
        return ignored

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
                update_only=self.update_only,
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

    # ----- changelog -----

    def _comparable(self, instance, name):
        """
        The stored value of `name` on `instance`, in a form two snapshots can be compared by.

        A foreign key is read through its attname so the comparison stays an id and never fetches
        the related row; a many-to-many is read as its sorted ids.
        """
        from django.core.exceptions import FieldDoesNotExist

        try:
            field = instance._meta.get_field(name)
        except FieldDoesNotExist:
            # A serializer field with no model field behind it has nothing stored to compare.
            return None, False
        if field.many_to_many:
            return sorted(getattr(instance, name).values_list("pk", flat=True)), True
        return getattr(instance, field.attname, None), True

    def _snapshot(self, instance, names) -> typing.Dict:
        snapshot = {}
        for name in names:
            value, exists = self._comparable(instance, name)
            if exists:
                snapshot[name] = value
        return snapshot

    def changelog_fields(self, serializer) -> typing.List[str]:
        """
        Fields to record before/after: everything the serializer resolved for this row, including
        values it injected itself, since those are writes the operator did not ask for and would
        otherwise go unrecorded.

        EXTRA_EXCLUDED_FIELDS is deliberately NOT subtracted. That denylist says a field is not an
        editable column, which is a different question from whether a write to it is worth
        reporting: a field kept out of the sheet can still be written by the serializer, and that
        is exactly the write an operator has no other way to find out about.
        """
        skipped = self.EXCLUDED_FIELDS | set(self.match_column_names) | {"id"}
        return [name for name in serializer.validated_data if name not in skipped]

    @classmethod
    def render_change_value(cls, value) -> str:
        """
        One-line rendering of a stored value. Prose fields hold newlines and run to paragraphs,
        either of which would break the one-line-per-row format, so whitespace is collapsed and a
        long value is cut — the line says which field moved and how it starts, not the full text.

        An enum renders as its member name, which is the token a sheet writes, so a log line can be
        grepped for what the operator typed. Its label is translated and is not unique across
        members, so two different values can print identically.
        """
        if isinstance(value, enum.Enum):
            return value.name
        text = " ".join(str(value).split())
        if len(text) > cls.CHANGELOG_VALUE_CHARS:
            return text[: cls.CHANGELOG_VALUE_CHARS] + "..."
        return text

    def print_row_change(self, row_number: int, instance, before: typing.Dict, after: typing.Dict) -> bool:
        """
        Report the fields whose stored value moved, as one tab-separated line. Rows are updated in
        place and nothing else records what they held before, so this is the only account of it.
        Returns whether anything moved.
        """
        moved = []
        for name in before:
            if before[name] == after[name]:
                continue
            was, now = self.render_change_value(before[name]), self.render_change_value(after[name])
            if was == now:
                # Both values were cut back to the same text, so quoting them would show a change
                # from a value to itself. Name the field and say why it carries no values.
                moved.append(f"{name}=changed (first {self.CHANGELOG_VALUE_CHARS} chars identical)")
            else:
                moved.append(f"{name}={was}->{now}")
        if not moved:
            return False
        self.stdout.write(
            self.style.SUCCESS(
                f"ROW_UPDATED\t{self.model.__name__.lower()}={instance.pk}\trow={row_number}\t" + "\t".join(moved)
            )
        )
        return True

    @contextmanager
    def import_context(self):
        """
        Wraps the whole import, inside the transaction. Subclasses that need per-run state which
        writes when it closes (a figure import recomputes event review status there) enter it here,
        so those writes are covered by the same transaction a dry run rolls back.
        """
        yield

    @transaction.atomic
    def run_import(self, rows: typing.List[typing.Dict], request, dry_run: bool):
        with self.import_context():
            created, updated, unchanged = self.apply_rows(rows, request)

        # Reported once import_context has closed: it may write on exit, and Django refuses any
        # further query in an atomic block once rollback is flagged.
        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(f"DRY RUN: would create {created}, update {updated}; rolled back."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created {created}, updated {updated}."))
        if unchanged:
            self.stdout.write(self.style.NOTICE(f"{unchanged} of the updated rows had no effective change."))

    def apply_rows(self, rows: typing.List[typing.Dict], request) -> typing.Tuple[int, int, int]:
        """Validate every row, then persist. Returns (created, updated, unchanged)."""
        errors: typing.List[typing.Tuple[int, str, str]] = []
        prepared: typing.List[typing.Tuple] = []
        # Row number each targeted row was first seen on. Two rows aimed at one row would each
        # validate against its unmodified state and then both save, silently losing the earlier.
        # Keyed by the resolved primary key rather than the cell, so a sheet writing the same id
        # as a number on one row and as text on another is still one target.
        pk_rows: typing.Dict[typing.Any, int] = {}
        ignored_cells: typing.List[typing.Tuple[int, str]] = []

        # First pass: resolve + validate every row, collecting all errors (all-or-nothing).
        for index, raw_row in enumerate(rows, start=2):  # row 1 is the header
            row = self.prepare_row(raw_row, request)
            serializer, is_update, row_errors, ignored = row.serializer, row.is_update, row.errors, row.ignored_cells

            if is_update and serializer is not None:
                pk = serializer.instance.pk
                first_seen = pk_rows.get(pk)
                if first_seen is not None:
                    row_errors[self.match_column_names[0]] = (
                        f"{self.model.__name__} {pk} also appears on row {first_seen}; each row must target a distinct row"
                    )
                else:
                    pk_rows[pk] = index

            if row_errors:
                for field, message in row_errors.items():
                    errors.append((index, field, message))
            else:
                prepared.append((serializer, is_update, index))
                for cell in ignored:
                    ignored_cells.append((index, cell))

        if errors:
            self.stdout.write(self.style.ERROR(f"Import failed: {len(errors)} error(s); nothing committed."))
            for row_number, field, message in errors:
                self.stdout.write(self.style.ERROR(f"Row {row_number}: {field}: {message}"))
            raise CommandError("Import aborted due to validation errors.")

        # Second pass: persist. Duplicates are already rejected, so no row's snapshot can be
        # disturbed by another row's save.
        created = updated = unchanged = 0
        for serializer, is_update, row_number in prepared:
            fields = self.changelog_fields(serializer) if is_update else []
            before = self._snapshot(serializer.instance, fields) if is_update else {}
            instance = serializer.save()
            if is_update:
                updated += 1
                if not self.print_row_change(row_number, instance, before, self._snapshot(instance, fields)):
                    unchanged += 1
            else:
                created += 1

        self.print_ignored_cells(ignored_cells)
        return created, updated, unchanged

    def print_ignored_cells(self, ignored_cells: typing.List[typing.Tuple[int, str]]):
        """
        Report cells the serializer emptied. The row was still written, so this is not an error -
        but the sheet asked for something it did not get, and nothing else says so.
        """
        if not ignored_cells:
            return
        self.stdout.write(
            self.style.WARNING(
                f"{len(ignored_cells)} cell(s) were ignored: the serializer emptied them because they "
                "do not apply to the row as it stands. The rows themselves were still updated."
            )
        )
        for row_number, cell in ignored_cells:
            self.stdout.write(self.style.WARNING(f"CELL_IGNORED\trow={row_number}\t{cell}"))
