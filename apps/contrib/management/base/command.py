"""The reusable bulk-import management command base class."""

import datetime
import enum
import typing

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
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

    #: Field map per serializer class, built once per invocation.
    _fields_cache: typing.Optional[typing.Dict] = None

    def _serializer_fields(self, serializer_cls) -> typing.Dict:
        """
        The field map of a serializer class, built once and kept.

        Reading a cell asks what type its column is, and answering that used to construct a whole
        serializer — twice per cell, since both the date narrowing and the list splitting ask. On a
        wide serializer that is milliseconds per cell and dwarfs everything else the row does. The
        map only describes the columns, so it is the same for every row.
        """
        if self._fields_cache is None:
            self._fields_cache = {}
        if serializer_cls not in self._fields_cache:
            self._fields_cache[serializer_cls] = serializer_cls().fields
        return self._fields_cache[serializer_cls]

    def _writable_fields(self, serializer_cls) -> typing.List[str]:
        return [name for name, field in self._serializer_fields(serializer_cls).items() if not field.read_only]

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
        update_fields = self._serializer_fields(self.update_serializer)
        if self.update_only:
            return update_fields.get(column)
        create_fields = self._serializer_fields(self.create_serializer)
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
                if len(self.match_columns) > 1:
                    notes[column] = f"identifies the row; supply exactly one of {DISPLAY_SEP.join(self.match_column_names)}"
                elif self.update_only:
                    notes[column] = f"{column} of the row to update"
                else:
                    notes[column] = f"leave blank to create; set an existing {column} to update"
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

    #: Sheet rows whose match keys are resolved together. Resolving row by row costs one query per
    #: row, which on a large sheet is most of the run; a chunk costs one query per match column.
    #: Bounded so the instances of a chunk are the only ones held at a time.
    RESOLVE_CHUNK_SIZE = 1000

    def _match_field(self, field: str):
        """The model field a match column queries through. ``pk`` is a lookup, not a field name."""
        return self.model._meta.pk if field == "pk" else self.model._meta.get_field(field)

    @staticmethod
    def _chunks(rows: typing.Iterable[typing.Dict], size: int):
        """Yield (sheet row number of the first row, chunk), so a row keeps its number in the sheet."""
        chunk: typing.List[typing.Dict] = []
        start = 2  # row 1 is the header
        for raw_row in rows:
            chunk.append(raw_row)
            if len(chunk) == size:
                yield start, chunk
                start += len(chunk)
                chunk = []
        if chunk:
            yield start, chunk

    def resolve_chunk(self, chunk: typing.List[typing.Dict]) -> typing.Dict:
        """
        Resolve the match keys of a whole chunk, one query per match column.

        Returns {column: {coerced key: [instances]}}. Every match is kept, not just the first two,
        so an ambiguous key stays visible as more than one — a match field is not necessarily
        unique, since ``Figure.uuid`` carries whatever uuid an external import supplied.

        A key that will not coerce is left out and reported when its own row is prepared, so one
        bad cell cannot cost the chunk its query.
        """
        resolved: typing.Dict[str, typing.Dict] = {}
        for column, field in self.match_columns:
            model_field = self._match_field(field)
            keys = set()
            for raw_row in chunk:
                raw = raw_row.get(column)
                if is_empty(raw):
                    continue
                try:
                    keys.add(model_field.to_python(raw))
                except (DjangoValidationError, ValueError, TypeError):
                    continue
            if not keys:
                continue
            matches: typing.Dict[typing.Any, typing.List] = {}
            for instance in self.model.objects.filter(**{f"{field}__in": list(keys)}):
                matches.setdefault(getattr(instance, field) if field != "pk" else instance.pk, []).append(instance)
            resolved[column] = matches
        return resolved

    def resolve_row(self, column: str, field: str, key, resolved: typing.Optional[typing.Dict] = None):
        """
        Find the single row `key` names. Returns (instance, error_message); exactly one is set.

        With `resolved` from `resolve_chunk` the answer is already in memory; without it the row is
        queried on its own, which keeps the method usable for a single row.
        """
        model_field = self._match_field(field)
        try:
            coerced = model_field.to_python(key)
        except (DjangoValidationError, ValueError, TypeError):
            # A key column takes raw sheet text: a malformed uuid or a non-numeric id fails here.
            # Without this the framework's promise — every row checked, every error named with its
            # row — is replaced by a traceback that does not say which of thousands of rows is bad.
            return None, f"{key!r} is not a valid {column}"

        if resolved is not None and column in resolved:
            matches = resolved[column].get(coerced, [])
            ambiguous_ids = [instance.pk for instance in matches]
        else:
            queryset = self.model.objects.filter(**{field: coerced})
            matches = list(queryset[:2])
            ambiguous_ids = list(queryset.values_list("pk", flat=True)) if len(matches) > 1 else []

        if not matches:
            return None, f"no {self.model.__name__} found with {column} {key}"
        if len(matches) > 1:
            ids = ", ".join(str(pk) for pk in ambiguous_ids)
            return None, (f"{column} {key} matches more than one {self.model.__name__} ({ids}); cannot tell which to edit")
        return matches[0], None

    def prepare_row(self, raw_row: typing.Dict, request, resolved: typing.Optional[typing.Dict] = None):
        """Resolve a raw row and build its serializer. Returns a PreparedRow."""
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

        context = {"request": request}
        serializer = None
        if len(supplied) > 1:
            row_errors[supplied[0][0]] = f"exactly one of {names} is required; {len(supplied)} given"
        elif is_update:
            column, field = supplied[0]
            key = raw_row.get(column)
            instance, error = self.resolve_row(column, field, key, resolved)
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
        emptied or dropped is reported. An override that swaps one value for another is NOT seen:
        ReportSerializer.validate_report does that on its GIDD branch, setting
        filter_figure_start_after/end_before to the report year's bounds and is_public to True.
        Cells cleared on purpose are not overrides.
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
        self._fields_cache = None

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
                match_columns=self.match_column_names,
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
        value = getattr(instance, field.attname, None)
        if field.is_relation:
            return value, True
        # Through the field, because the after-snapshot reads the instance in memory and a
        # serializer may assign a type the column does not store: ReportSerializer writes a
        # datetime into a DateField, which would otherwise read as a change from
        # date(2020,1,1) to datetime(2020,1,1) while the stored value never moved.
        try:
            return field.to_python(value), True
        except DjangoValidationError:
            return value, True

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

    def row_change_line(self, row_number: int, instance, before: typing.Dict, after: typing.Dict) -> typing.Optional[str]:
        """
        The changelog line for a row whose stored values moved, or None when nothing moved. Rows are
        updated in place and nothing else records what they held before, so this is the only account
        of it.
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
            return None
        return f"ROW_UPDATED\t{self.model.__name__.lower()}={instance.pk}\trow={row_number}\t" + "\t".join(moved)

    @transaction.atomic
    def run_import(self, rows: typing.Iterable[typing.Dict], request, dry_run: bool):
        created, updated, unchanged = self.apply_rows(rows, request)

        # Reported after the work, because Django refuses any further query in an atomic block
        # once rollback is flagged.
        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(f"DRY RUN: would create {created}, update {updated}; rolled back."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created {created}, updated {updated}."))
        if unchanged:
            self.stdout.write(self.style.NOTICE(f"{unchanged} of the updated rows had no effective change."))

    def apply_rows(self, rows: typing.Iterable[typing.Dict], request) -> typing.Tuple[int, int, int]:
        """
        Validate and persist row by row. Returns (created, updated, unchanged).

        One row is resolved, validated and saved before the next is read, and nothing about it is
        retained afterwards. A serializer is an expensive object — it deep-copies every declared
        field on construction — so keeping one per row made a large sheet cost gigabytes and fail
        on memory before it wrote anything.

        Saving as we go does not weaken the all-or-nothing guarantee: `run_import` holds a
        transaction around this, so a validation error raised at the end discards every write.
        Once a row has failed, later rows are still validated but no longer saved, since the run
        is already going to roll back and the writes would be thrown away.

        What this does change: a row is validated against a database in which earlier rows are
        already written, where before every row saw the pristine state. Rows must target distinct
        model rows, so no row can see its own target altered — but a serializer that validates
        against the rest of the table (a uniqueness check, say) would now see the earlier writes.
        No importer does that today.
        """
        errors: typing.List[typing.Tuple[int, str, str]] = []
        # Row number each targeted row was first seen on. Two rows aimed at one row would each
        # validate against its unmodified state and then both save, silently losing the earlier.
        # Keyed by the resolved primary key rather than the cell, so a sheet writing the same id
        # as a number on one row and as text on another is still one target.
        pk_rows: typing.Dict[typing.Any, int] = {}
        ignored_cells: typing.List[typing.Tuple[int, str]] = []
        # Changelog lines are held back rather than written as they happen: a run that fails at its
        # last row commits nothing, and lines already printed would claim changes that never landed.
        changelog: typing.List[str] = []
        created = updated = unchanged = 0

        for chunk_start, chunk in self._chunks(rows, self.RESOLVE_CHUNK_SIZE):
            # One query per match column for the whole chunk, rather than one per row.
            resolved = self.resolve_chunk(chunk)
            for offset, raw_row in enumerate(chunk):
                index = chunk_start + offset
                row = self.prepare_row(raw_row, request, resolved)
                serializer, is_update, row_errors, ignored = (
                    row.serializer,
                    row.is_update,
                    row.errors,
                    row.ignored_cells,
                )

                if is_update and serializer is not None:
                    pk = serializer.instance.pk
                    first_seen = pk_rows.get(pk)
                    if first_seen is not None:
                        row_errors[self.match_column_names[0]] = (
                            f"{self.model.__name__} {pk} also appears on row {first_seen}; "
                            "each row must target a distinct row"
                        )
                    else:
                        pk_rows[pk] = index

                if row_errors:
                    for field, message in row_errors.items():
                        errors.append((index, field, message))
                    continue

                for cell in ignored:
                    ignored_cells.append((index, cell))

                if errors:
                    # The run will roll back, so writing this row buys nothing. Keep reading, though:
                    # the operator is owed every error in the sheet, not just the first.
                    continue

                fields = self.changelog_fields(serializer) if is_update else []
                before = self._snapshot(serializer.instance, fields) if is_update else {}
                instance = serializer.save()
                if is_update:
                    updated += 1
                    line = self.row_change_line(index, instance, before, self._snapshot(instance, fields))
                    if line is None:
                        unchanged += 1
                    else:
                        changelog.append(line)
                else:
                    created += 1

        if errors:
            self.stdout.write(self.style.ERROR(f"Import failed: {len(errors)} error(s); nothing committed."))
            for row_number, field, message in errors:
                self.stdout.write(self.style.ERROR(f"Row {row_number}: {field}: {message}"))
            raise CommandError("Import aborted due to validation errors.")

        for line in changelog:
            self.stdout.write(self.style.SUCCESS(line))
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
