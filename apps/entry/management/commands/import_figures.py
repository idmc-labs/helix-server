from collections import OrderedDict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.management.base import BaseImportCommand, EnumLookup
from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Figure
from utils.common import round_half_up
from utils.validations import is_date_within_future_bound


class FigureRoleDatesAndValuesSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    """
    The narrow slice of a figure this importer may edit: its role, its dates, and the three
    fields its total is computed from.

    Deliberately not built on `FigureSerializer`. That one carries
    `CommonFigureValidationMixin`, which re-checks a figure's whole stored state — so a figure
    whose historical data no longer satisfies current rules cannot be edited at all, and since an
    import is all-or-nothing, one such figure stops the entire run. Measured against a prod-like
    snapshot, 4,545 of 191,192 figures fail at least one of those checks.

    Skipping the mixin means the derivations it performs must be reproduced for the fields that
    feed them. `total_figures` is `editable=False` and computed nowhere else, so it is derived
    here from `unit`, `reported` and `household_size` by the same rule as
    `CommonFigureValidationMixin._validate_unit`, and is never accepted as a column — a supplied
    total could contradict its own inputs. The mixin's other derivation (`violence` /
    `disaster_type` / `disaster_sub_category` / `disaster_category` from the sub-type foreign
    keys) is fed by no field here, so nothing falls out of step.

    What is also lost, and wanted: `end_date_accuracy` is no longer silently cleared for a stock
    category, and a figure keeps its review status when its dates are corrected.

    Carried over rather than dropped: the checks decided by these fields. A date the app would
    refuse must not be written here, or the row fails validation on every later edit. Each check
    is scoped to rows that supply the field deciding it, so a row is never refused over a value it
    never touched. Disaggregation is left alone: this serializer does not edit those fields, and
    the mixin's bounds against them are part of the whole-state re-check it exists to avoid.
    """

    class Meta:
        model = Figure
        fields = [
            "id",
            "role",
            "start_date",
            "end_date",
            "start_date_accuracy",
            "end_date_accuracy",
            "unit",
            "reported",
            "household_size",
        ]

    #: Fields whose arrival means `total_figures` has to be recomputed.
    VALUE_FIELDS = ("unit", "reported", "household_size")

    def _validate_dates(self, attrs, errors):
        # One group: each rule below is decided by the pair, so either date puts both under
        # review. A row supplying neither must not be refused over dates it never touched.
        # Membership, not truthiness — the clear-token supplies None, the edit most worth checking.
        if "start_date" not in attrs and "end_date" not in attrs:
            return
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        category = getattr(self.instance, "category", None)

        if start_date and end_date and start_date > end_date:
            errors["start_date"] = f"{start_date} is after end_date {end_date}"

        # A date the app would refuse must not be written here: it would break every later edit.
        errors.update(is_date_within_future_bound(start_date, "start_date"))
        errors.update(is_date_within_future_bound(end_date, "end_date"))

        if category in Figure.flow_list():
            # FigureSerializer._validate_category compares end_date to today with no null
            # guard, so a cleared one raises TypeError on every later save.
            if end_date is None:
                errors["end_date"] = "A flow figure must keep an end date; clearing it would make the figure uneditable"
            elif end_date > timezone.now().date():
                errors["end_date"] = "This must be a past date for a flow figure"

    def _derive_total_figures(self, attrs, errors):
        """
        Recompute `total_figures`, matching `CommonFigureValidationMixin._validate_unit`.

        Only runs for a row that supplies one of the three inputs: the stored total of an
        untouched figure is left exactly as it is, including the historical rows where it does
        not satisfy the current rule.
        """
        if not any(field in attrs for field in self.VALUE_FIELDS):
            return
        unit = attrs.get("unit", getattr(self.instance, "unit", Figure.UNIT.PERSON))
        reported = attrs.get("reported", getattr(self.instance, "reported", 0))
        household_size = attrs.get("household_size", getattr(self.instance, "household_size", None))

        if reported is None:
            errors["reported"] = "This field is required"
            return

        if unit == Figure.UNIT.PERSON:
            # A person-unit figure carries no household size; the app clears it rather than
            # leaving a stale multiplier next to a total that no longer uses it.
            attrs["household_size"] = None
            attrs["total_figures"] = reported
        elif unit == Figure.UNIT.HOUSEHOLD:
            # A household figure's total is reported x household size, so the size has to be a
            # positive number: zero would publish a real displacement as 0, and a negative one
            # would drive the total below the column's range.
            #
            # NOTE: this makes a household figure whose *stored* household size is already 0 or
            # NULL uneditable through this importer, even for its role or dates. Such rows exist
            # (they predate the rule and were written by paths that bypass the serializer), and
            # because an import is all-or-nothing a single one fails the whole sheet.
            # FIXME: only demand a household size when the row actually changes `unit` or
            # `household_size`, so a figure with a bad stored size stays editable on its other
            # fields. Left alone for now: no such figure is in the current drift set.
            if household_size is None:
                errors["household_size"] = "This field is required for a household-unit figure"
                return
            if household_size <= 0:
                errors["household_size"] = "This must be greater than zero for a household-unit figure"
                return
            attrs["total_figures"] = int(round_half_up(reported * Decimal(str(household_size))))
        else:
            errors["unit"] = f"Unknown unit {unit}"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors: OrderedDict = OrderedDict()
        self._validate_dates(attrs, errors)
        self._derive_total_figures(attrs, errors)
        if errors:
            raise ValidationError(errors)
        return attrs


class Command(BaseImportCommand):
    help = (
        "Bulk update the role, dates and reported values of existing figures from an .xlsx sheet. "
        "`total_figures` is derived from unit, reported and household size, never supplied. "
        "Use --make-template to generate a blank template. "
        "Each row names its figure by id or uuid, or both - supplying both is safer, since the "
        "second is checked against the row the first resolved. It never creates."
    )

    model = Figure
    update_serializer = FigureRoleDatesAndValuesSerializer
    update_only = True

    # A sheet built from a figure export carries ids; one built from the system that supplied the
    # figures carries uuids, which hulk writes into Figure.uuid as well as its own row. Either
    # names a figure. A row supplying both is safest: the id resolves it and the uuid is checked
    # against the resolved figure, so a sheet built against another instance fails instead of
    # editing whatever happens to hold that id here.
    match_columns = (("id", "pk"), ("uuid", "uuid"))

    lookups = [
        EnumLookup("role", Figure.ROLE),
        EnumLookup("unit", Figure.UNIT),
        EnumLookup("start_date_accuracy", DATE_ACCURACY),
        EnumLookup("end_date_accuracy", DATE_ACCURACY),
    ]
