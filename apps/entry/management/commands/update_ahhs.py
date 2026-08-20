import csv
import os
import re
import typing
from collections import Counter
from datetime import datetime
from decimal import Decimal
from functools import cached_property
from typing import Union

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from requests.structures import CaseInsensitiveDict

from apps.country.models import Country, HouseholdSize
from apps.country.serializers import HouseholdSizeCliImportSerializer
from apps.entry.models import Figure
from apps.users.models import User
from apps.users.utils import HelixInternalBot
from helix.managers import BulkUpdateManager
from utils.common import round_half_up

DataRow = typing.TypedDict(
    "DataRow",
    {
        "Year": str,
        "AHHS": str,
        "ISO3": str,
        "Data source category": str,
        "Reference date": str,
        "Source": typing.Optional[str],  # We have default value "No data"
        "Source link": typing.Optional[str],  # This should be nullable
        "Notes": typing.Optional[str],
        "IDMC update date": typing.Optional[str],
    },
)


# Figure update modes for --figure-update-mode.
FIGURE_UPDATE_MODE_NONE = "none"  # Touch no figures; import AHHS records only.
FIGURE_UPDATE_MODE_NUMBERS = "numbers"  # Update household_size, total_figures, excerpt_idu.
FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE = "numbers_and_note"  # numbers + append the retroactive calculation_logic note.
FIGURE_UPDATE_MODES = [
    FIGURE_UPDATE_MODE_NONE,
    FIGURE_UPDATE_MODE_NUMBERS,
    FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE,
]

# Data fields that decide whether an incoming AHHS row differs from the current active record.
# Metadata churn fields (created_at/modified_at/created_by/last_modified_by/is_active) are excluded on purpose.
HOUSEHOLD_SIZE_COMPARISON_FIELDS = (
    "size",
    "reference_date",
    "gap_filling_method",
    "data_source_category",
    "source",
    "source_link",
    "notes",
)


def calculate_gap_filling_method(year, reference_year):
    if year == reference_year:
        return HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR
    if year < reference_year:
        return HouseholdSize.GAP_FILLING_METHOD.BACKWARD_FILLING
    return HouseholdSize.GAP_FILLING_METHOD.FORWARD_FILLING


def format_date(date: Union[str, datetime]) -> datetime:
    if isinstance(date, datetime):
        return date

    return datetime.strptime(date, "%Y-%m-%d")


def total_figures_pattern(total: int) -> typing.Pattern:
    """
    Match `total` in prose at word boundaries, tolerating any thousands-comma placement.
    `1000` becomes `1,?0,?0,?0`, so both "1000" and "1,000" match.
    """
    return re.compile("\\b" + ",?".join(str(total)) + "\\b")


# An excerpt states two different quantities: the person total (derived from AHHS, and the only one
# worth substituting) and the household count (`reported`, which AHHS does not change). A bare
# numeric match can also land on a calendar day or inside a longer number, so matches are only
# substituted when none of these contexts apply.
MONTH_NAME = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
HOUSEHOLD_NOUN = r"(?:houses?|households?|homes?|famil(?:y|ies)|propert(?:y|ies)|dwellings?|shelters?)"

_DATE_AFTER = re.compile(r"\s*(?:" + MONTH_NAME + r"\b|(?:st|nd|rd|th)\b|[/-]\s*\d)", re.IGNORECASE)
_DATE_BEFORE = re.compile(MONTH_NAME + r"\s*$|[/-]\s*$", re.IGNORECASE)
# The noun may trail an adjective or two ("1,200 newly destroyed houses"), but not another number,
# which would belong to a different quantity.
_HOUSEHOLD_AFTER = re.compile(r"\s*(?:[^\W\d_]+\s+){0,2}" + HOUSEHOLD_NOUN + r"\b", re.IGNORECASE)
_NUMBER_AFTER = re.compile(r"\s*[,.]\d")
_NUMBER_BEFORE = re.compile(r"\d[,.]\s*$")


class VerificationItem(typing.NamedTuple):
    """A figure whose numbers moved but whose excerpt could not be updated to match."""

    figure_pk: int
    iso3: str
    reason: str
    old_total: int
    new_total: int
    excerpt: str


class FigureChange(typing.NamedTuple):
    """
    What this command altered on one figure. Figures are updated in place, so unlike an archived
    AHHS row nothing else records what they held before.

    Numeric fields carry both values. Text fields are recorded as changed but not by value: a log
    line cannot hold prose without flattening its newlines, so the copy would not be faithful.
    """

    figure_pk: int
    iso3: str
    year: int
    old_size: float
    new_size: float
    old_total: int
    new_total: int
    excerpt_rewritten: bool
    note_appended: bool


class FigureRunLog:
    """
    What a figure pass accumulates. The per-figure changelog is held back and reported once the
    pass is done, so the running output stays to one short line per figure.
    """

    def __init__(self):
        self.tally: Counter = Counter()
        self.changes: typing.List[FigureChange] = []
        self.needs_verification: typing.List[VerificationItem] = []


class ExcerptRewrite(typing.NamedTuple):
    text: str
    substitutions: int
    #: Matches left alone because they read as a date, a household count, or part of a longer number.
    ambiguous_matches: int


def _is_person_total(excerpt: str, match) -> bool:
    before, after = excerpt[: match.start()], excerpt[match.end() :]
    if _DATE_AFTER.match(after) or _DATE_BEFORE.search(before):
        return False
    if _HOUSEHOLD_AFTER.match(after):
        return False
    return not (_NUMBER_AFTER.match(after) or _NUMBER_BEFORE.search(before))


def rewrite_excerpt_idu(excerpt: str, old_total: int, new_total: int) -> ExcerptRewrite:
    """
    Replace `old_total` with `new_total` wherever the excerpt states it as the person total,
    keeping the thousands grouping the excerpt already used.
    """
    substitutions = ambiguous = 0

    def replace(match: typing.Match[str]) -> str:
        nonlocal substitutions, ambiguous
        if not _is_person_total(excerpt, match):
            ambiguous += 1
            return match.group()
        substitutions += 1
        return f"{new_total:,}" if "," in match.group() else str(new_total)

    text = total_figures_pattern(old_total).sub(replace, excerpt)
    return ExcerptRewrite(text, substitutions, ambiguous)


class Command(BaseCommand):
    help = "Update AHHS based on new household size data."
    required_csv_headers = {
        "Year",
        "AHHS",
        "ISO3",
        "Data source category",
        "Reference date",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file_path",
            type=str,
            help="Path to the CSV file containing the data.",
        )
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="AHHS year to be updated",
        )
        parser.add_argument(
            "--figure-update-mode",
            choices=FIGURE_UPDATE_MODES,
            required=True,
            help=(
                "How figures are updated: "
                f"'{FIGURE_UPDATE_MODE_NONE}' touches no figures; "
                f"'{FIGURE_UPDATE_MODE_NUMBERS}' updates household_size, total_figures and excerpt_idu; "
                f"'{FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE}' also appends the retroactive note to calculation_logic."
            ),
        )
        parser.add_argument(
            "--retroactive-update-date",
            type=str,
            help=(
                "Date (ISO format) when AHHS values were retroactively changed. "
                f"Required when --figure-update-mode={FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE}."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the full update inside a transaction, then roll back without committing.",
        )

    # NOTE: This function cannot be cached
    def iso3_to_household_sizes(self, year: int) -> typing.Dict[str, typing.Optional[HouseholdSize]]:
        household_sizes = HouseholdSize.objects.filter(year=year, is_active=True).select_related("country")
        return typing.cast(
            typing.Dict[str, typing.Optional[HouseholdSize]],
            CaseInsensitiveDict({size.country.iso3: size for size in household_sizes}),
        )

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

    @staticmethod
    def _normalize_for_comparison(value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return value

    @classmethod
    def household_size_unchanged(cls, existing: HouseholdSize, item: typing.Dict) -> bool:
        return all(
            cls._normalize_for_comparison(getattr(existing, field)) == cls._normalize_for_comparison(item.get(field))
            for field in HOUSEHOLD_SIZE_COMPARISON_FIELDS
        )

    def update_household_sizes(self, validated_data: typing.List[typing.Dict], tally: Counter) -> typing.List[typing.Dict]:
        """
        Replace the active AHHS records that differ from the incoming rows.
        Returns only the items whose `size` moved, since those are the only ones whose figures
        need revisiting; metadata-only edits leave every derived figure correct.
        """
        size_changed_items = []
        for item in validated_data:
            existing_active = HouseholdSize.objects.filter(
                country=item["country"],
                year=item["year"],
                is_active=True,
            )
            active_records = list(existing_active)
            # Only a single clean active record can be judged "unchanged"; dirty duplicates fall through to be replaced.
            if len(active_records) == 1 and self.household_size_unchanged(active_records[0], item):
                tally["unchanged"] += 1
                continue

            # A country with no active record has no previous value, so its figures are in scope too.
            size_changed = {record.size for record in active_records} != {item["size"]}

            # NOTE: deactivating previous values. The archived row is the record of what this
            # country-year held before, so the run reports only counts.
            existing_active.update(is_active=False)

            new_ahhs = HouseholdSize.objects.create(
                **item,
            )
            # NOTE: Because of updates to created_at/modified_at we haven't used bulk_create
            HouseholdSize.objects.filter(pk=new_ahhs.pk).update(
                created_at=item["created_at"],
                last_modified_by=item["last_modified_by"],
                modified_at=item["modified_at"],
            )
            tally["created"] += 1
            if size_changed:
                tally["size_changed"] += 1
                size_changed_items.append(item)
            else:
                tally["metadata_only"] += 1
        return size_changed_items

    def process_household_size_row(self, row: DataRow, year: int) -> typing.Optional[typing.Dict]:
        if row["Year"] != str(year):
            return None

        country_id = None
        if iso3 := row.get("ISO3"):
            country_id = self.iso3_to_country_id.get(iso3)

        created_at = format_date(datetime.today())

        modified_at = created_at
        if idmc_update_date := row.get("IDMC update date"):
            modified_at = format_date(idmc_update_date)

        # NOTE: For some regions we do not have permanent residence so AHHS can be zero
        size = row["AHHS"]
        if size is None or size == "":
            size = 0

        reference_year = datetime.strptime(row["Reference date"], "%Y-%m-%d").year
        gap_filling_method = calculate_gap_filling_method(int(row["Year"]), reference_year)

        return {
            # Data from csv
            "size": size,
            "year": row["Year"],
            "reference_date": row["Reference date"],
            "gap_filling_method": gap_filling_method,
            "country": country_id,
            "data_source_category": row["Data source category"],
            "source": row.get("Source", "No Data"),
            "source_link": row.get("Source link", ""),
            "notes": row.get("Notes"),
            # Additional metadata
            "created_by": self.admin_user.pk,
            "last_modified_by": self.admin_user.pk,
            "created_at": created_at,
            "modified_at": modified_at,
            "is_active": True,
        }

    def update_household_sizes_from_csv(self, file_path: str, year: int, tally: Counter) -> typing.List[typing.Dict]:
        with open(file_path, "r") as file:
            reader = csv.DictReader(file)

            csv_headers = set(reader.fieldnames or [])
            missing_headers = self.required_csv_headers.difference(csv_headers)
            if missing_headers:
                raise ValueError(f"Missing required headers in CSV: {', '.join(missing_headers)}")

            processed_rows = []
            total = 0

            for row in reader:
                if processed_row := self.process_household_size_row(typing.cast(DataRow, row), year):
                    total += 1
                    processed_rows.append(processed_row)

            if len(processed_rows) != total:
                self.stdout.write(self.style.NOTICE(f"Processed {len(processed_rows)} out of {total} AHHS items from CSV"))
            else:
                self.stdout.write(f"Processed {len(processed_rows)} out of {total} AHHS items from CSV")

            size_changed_items = []
            serializer = HouseholdSizeCliImportSerializer(data=processed_rows, many=True)
            if serializer.is_valid():
                size_changed_items = self.update_household_sizes(serializer.validated_data, tally)
            else:
                for i, errors in enumerate(serializer.errors):
                    if errors:
                        self.stdout.write(self.style.ERROR(f"---- Error in row {i + 1} ---- "))
                        self.stdout.write(self.style.ERROR(f"Row data: {processed_rows[i]}"))
                    for field, error in errors.items():
                        self.stdout.write(self.style.ERROR(f"'{field}': {error}"))
                raise Exception("Import failed")

            return size_changed_items

    def update_figure(
        self,
        bulk_mgr: BulkUpdateManager,
        figure: Figure,
        old_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        new_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        retroactive_update_date: typing.Optional[datetime],
        mode: str,
        log: "FigureRunLog",
    ):
        old_household_size = old_household_sizes.get(figure.country.iso3)
        if old_household_size is not None and figure.household_size != old_household_size.size:
            log.tally["skipped"] += 1
            log.needs_verification.append(
                VerificationItem(
                    figure.pk,
                    figure.country.iso3,
                    f"household size {figure.household_size} does not match the AHHS on record "
                    f"({old_household_size.size}); figure left untouched",
                    figure.total_figures,
                    figure.total_figures,
                    figure.excerpt_idu or "",
                )
            )
            return

        old_household_size = figure.household_size
        new_household_size = new_household_sizes.get(figure.country.iso3)
        if new_household_size is None:
            log.tally["skipped"] += 1
            log.needs_verification.append(
                VerificationItem(
                    figure.pk,
                    figure.country.iso3,
                    f"no active AHHS on record for {figure.country.iso3}; figure left untouched",
                    figure.total_figures,
                    figure.total_figures,
                    figure.excerpt_idu or "",
                )
            )
            return

        if old_household_size == new_household_size.size:
            log.tally["unchanged"] += 1
            return

        if new_household_size.size == 0:
            log.tally["skipped"] += 1
            return

        figure.household_size = new_household_size.size

        old_total_figures = figure.total_figures
        new_total_figures = int(round_half_up(figure.reported * Decimal(str(figure.household_size))))
        figure.total_figures = new_total_figures
        log.tally["changed"] += 1

        excerpt_rewritten = False
        note_appended = False

        if old_total_figures != new_total_figures:
            if figure.excerpt_idu:
                rewrite = rewrite_excerpt_idu(figure.excerpt_idu, old_total_figures, new_total_figures)

                if rewrite.substitutions:
                    excerpt_rewritten = True
                    figure.excerpt_idu = rewrite.text
                    log.tally["excerpt_rewritten"] += 1
                elif rewrite.ambiguous_matches:
                    log.tally["excerpt_ambiguous"] += 1
                    log.needs_verification.append(
                        VerificationItem(
                            figure.pk,
                            figure.country.iso3,
                            "total appears only as a date, a household count or part of a longer number",
                            old_total_figures,
                            new_total_figures,
                            figure.excerpt_idu,
                        )
                    )
                elif total_figures_pattern(figure.reported).search(figure.excerpt_idu):
                    # The excerpt states the household count rather than the person total, so the
                    # AHHS change leaves its wording correct.
                    log.tally["excerpt_states_household_count"] += 1
                else:
                    log.tally["excerpt_no_figure_stated"] += 1
                    log.needs_verification.append(
                        VerificationItem(
                            figure.pk,
                            figure.country.iso3,
                            "excerpt states neither the person total nor the household count",
                            old_total_figures,
                            new_total_figures,
                            figure.excerpt_idu,
                        )
                    )

            if mode == FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE:
                append_calculation_logic = (
                    f"On {retroactive_update_date.day} of {retroactive_update_date.strftime('%B')} "
                    f"{retroactive_update_date.year}, there was a retrospective update in AHHS; "
                    f"the value changed from {old_household_size} to {new_household_size.size} and "
                    f"the total figure changed from {old_total_figures} to {new_total_figures}. "
                    "Therefore, the text in the analysis may reflect old value."
                )
                if figure.calculation_logic:
                    figure.calculation_logic = f"{figure.calculation_logic}\n\n{append_calculation_logic}"
                else:
                    figure.calculation_logic = append_calculation_logic
                note_appended = True
                log.tally["note_appended"] += 1

        log.changes.append(
            FigureChange(
                figure.pk,
                figure.country.iso3,
                figure.start_date.year,
                old_household_size,
                new_household_size.size,
                old_total_figures,
                new_total_figures,
                excerpt_rewritten,
                note_appended,
            )
        )
        bulk_mgr.add(figure)

    def update_figures(
        self,
        year: int,
        old_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        new_household_sizes: typing.Dict[str, typing.Optional[HouseholdSize]],
        filter_countries: typing.Set[str],
        retroactive_update_date: typing.Optional[datetime],
        mode: str,
        log: "FigureRunLog",
    ):
        update_fields = ["household_size", "total_figures", "excerpt_idu"]
        if mode == FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE:
            update_fields.append("calculation_logic")
        bulk_mgr = BulkUpdateManager(
            update_fields,
            chunk_size=1000,
        )

        figures = Figure.objects.filter(
            unit=Figure.UNIT.HOUSEHOLD,
            # NOTE: in the frontend we are using "start_date" to get household size
            start_date__year=year,
            country__in=filter_countries,
        )
        for figure in figures:
            self.update_figure(
                bulk_mgr,
                figure,
                old_household_sizes,
                new_household_sizes,
                retroactive_update_date,
                mode,
                log,
            )

        bulk_mgr.done()
        self.stdout.write(self.style.SUCCESS(f"Updated figures: {bulk_mgr.summary()}"))

    def print_figure_changelog(self, changes: typing.List[FigureChange]):
        """
        Report what this run altered on each figure, naming only the fields that moved.

        Figures are updated in place, so this is the only record of what they held before; an AHHS
        row keeps its own history by being archived instead. It is also the only per-figure output,
        emitted once the pass is done as one tab-separated record so a run log loads as a table.
        """
        if not changes:
            return
        self.stdout.write(self.style.SUCCESS(f"{len(changes)} figures changed. Altered fields follow."))
        for item in changes:
            fields = [f"household_size={item.old_size}->{item.new_size}"]
            if item.old_total != item.new_total:
                fields.append(f"total_figures={item.old_total}->{item.new_total}")
            if item.excerpt_rewritten:
                fields.append("excerpt_idu=rewritten")
            if item.note_appended:
                fields.append("calculation_logic=note_appended")
            self.stdout.write(
                self.style.SUCCESS(
                    f"FIGURE_CHANGED\tfigure={item.figure_pk}\tcountry={item.iso3}\tyear={item.year}\t" + "\t".join(fields)
                )
            )

    def print_manual_verification(self, needs_verification: typing.List[VerificationItem]):
        """
        List the figures whose household size and total moved but whose excerpt could not be
        rewritten to match, so a person can reword them. One tab-separated line each, prefixed
        with MANUAL_VERIFICATION so a run log can be grepped straight into a worklist.
        """
        if not needs_verification:
            return
        self.stdout.write(
            self.style.WARNING(
                f"{len(needs_verification)} figures need manual verification: their excerpt could not "
                "be updated, or their household size could not be reconciled with the AHHS on record."
            )
        )
        for item in needs_verification:
            excerpt = " ".join(item.excerpt.split())
            self.stdout.write(
                self.style.WARNING(
                    "MANUAL_VERIFICATION\t"
                    f"figure={item.figure_pk}\tcountry={item.iso3}\t"
                    f"total={item.old_total}->{item.new_total}\treason={item.reason}\texcerpt={excerpt}"
                )
            )

    def print_summary(
        self,
        household_tally: Counter,
        figure_log: typing.Optional["FigureRunLog"],
        dry_run: bool,
    ):
        self.stdout.write(
            self.style.SUCCESS(
                f"AHHS: created {household_tally['created']} "
                f"(value changed {household_tally['size_changed']}, metadata only {household_tally['metadata_only']}), "
                f"unchanged {household_tally['unchanged']}"
            )
        )
        if figure_log is not None:
            figure_tally = figure_log.tally
            self.stdout.write(
                self.style.SUCCESS(
                    f"Figures: changed {figure_tally['changed']}, skipped {figure_tally['skipped']}, "
                    f"unchanged {figure_tally['unchanged']}, notes appended {figure_tally['note_appended']}"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Excerpts: rewritten {figure_tally['excerpt_rewritten']}, "
                    f"ambiguous {figure_tally['excerpt_ambiguous']}, "
                    f"state the household count {figure_tally['excerpt_states_household_count']}, "
                    f"state no figure {figure_tally['excerpt_no_figure_stated']}"
                )
            )
            needing_verification = (
                figure_tally["excerpt_ambiguous"] + figure_tally["excerpt_no_figure_stated"] + figure_tally["skipped"]
            )
            style = self.style.WARNING if needing_verification else self.style.SUCCESS
            self.stdout.write(style(f"Figures needing manual verification: {needing_verification}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: all changes rolled back; nothing was committed."))

    @transaction.atomic()
    def handle(self, *args, **kwargs):
        """
        Entry point for processing the CSV file to update Household Size.
        """
        csv_file_path = kwargs["csv_file_path"]
        year = kwargs["year"]
        mode = kwargs["figure_update_mode"]
        dry_run = kwargs["dry_run"]
        retroactive_update_date = kwargs["retroactive_update_date"]

        if mode == FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE and not retroactive_update_date:
            raise CommandError(
                f"--retroactive-update-date is required when --figure-update-mode={FIGURE_UPDATE_MODE_NUMBERS_AND_NOTE}"
            )

        if not os.path.exists(csv_file_path):
            raise CommandError(f"CSV file path does not exist: {csv_file_path}")

        household_tally: Counter = Counter()
        old_household_sizes_map = self.iso3_to_household_sizes(year)

        size_changed_household_sizes = self.update_household_sizes_from_csv(csv_file_path, year, household_tally)

        figure_log: typing.Optional[FigureRunLog] = None
        if mode != FIGURE_UPDATE_MODE_NONE:
            countries_set = set(x["country"].pk for x in size_changed_household_sizes)
            new_household_sizes_map = self.iso3_to_household_sizes(year)
            figure_log = FigureRunLog()
            self.update_figures(
                year,
                old_household_sizes_map,
                new_household_sizes_map,
                countries_set,
                format_date(retroactive_update_date) if retroactive_update_date else None,
                mode,
                figure_log,
            )

        if figure_log is not None:
            self.print_figure_changelog(figure_log.changes)
            self.print_manual_verification(figure_log.needs_verification)
        self.print_summary(household_tally, figure_log, dry_run)

        if dry_run:
            transaction.set_rollback(True)
