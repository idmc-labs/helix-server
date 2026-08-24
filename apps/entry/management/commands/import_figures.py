from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers

from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.management.base import BaseImportCommand, EnumLookup
from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Figure
from utils.validations import is_date_within_future_bound


class FigureRoleAndDatesSerializer(MetaInformationSerializerMixin, serializers.ModelSerializer):
    """
    The narrow slice of a figure this importer may edit: its role and its dates.

    Deliberately not built on `FigureSerializer`. That one carries
    `CommonFigureValidationMixin`, which re-checks a figure's whole stored state — so a figure
    whose historical data no longer satisfies current rules cannot be edited at all, and since an
    import is all-or-nothing, one such figure stops the entire run. Measured against a prod-like
    snapshot, 4,545 of 191,192 figures fail at least one of those checks.

    The mixin also derives values, which is why skipping it is only safe for this field set: it
    computes `total_figures` (`editable=False`, computed nowhere else) from `reported`,
    `household_size` and `unit`, and denormalises `violence` / `disaster_type` /
    `disaster_sub_category` / `disaster_category` from the sub-type foreign keys. None of the five
    fields here feed either, so nothing needs deriving and nothing falls out of step.

    What is also lost, and wanted: `end_date_accuracy` is no longer silently cleared for a stock
    category, and a figure keeps its review status when its dates are corrected.

    What had to be carried over rather than dropped: the checks that are themselves decided by
    these six fields. A date the app would refuse must not be written here, or the row fails
    validation on every later edit — the very trap this class exists to avoid.
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
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        errors = OrderedDict()

        # Every rule here is decided by the row as it will end up — the supplied value, else the
        # stored one — so a sheet that moves only one of a pair still gets checked against the
        # other. Anything needing a field outside this serializer's six is left to the app.
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        category = getattr(self.instance, "category", None)

        if start_date and end_date and start_date > end_date:
            errors["start_date"] = f"{start_date} is after end_date {end_date}"

        # A date the app itself would refuse must not be written here either: the row would then
        # fail validation on every later edit, which is the trap this serializer exists to avoid.
        errors.update(is_date_within_future_bound(start_date, "start_date"))
        errors.update(is_date_within_future_bound(end_date, "end_date"))

        if category in Figure.flow_list():
            # FigureSerializer._validate_category compares a flow figure's end_date against today
            # without a null guard, so clearing it leaves a row that raises TypeError on every
            # later save. Its year_difference also goes null, dropping it out of flow reporting.
            if end_date is None:
                errors["end_date"] = "A flow figure must keep an end date; clearing it would make the figure uneditable"
            elif end_date > timezone.now().date():
                errors["end_date"] = "This must be a past date for a flow figure"

        if errors:
            raise ValidationError(errors)
        return attrs


class Command(BaseImportCommand):
    help = (
        "Bulk update the role and dates of existing figures from an .xlsx sheet. "
        "Use --make-template to generate a blank template. "
        "Each row names its figure by either id or uuid, exactly one; it never creates."
    )

    model = Figure
    update_serializer = FigureRoleAndDatesSerializer
    update_only = True

    # A sheet built from a figure export carries ids; one built from the system that supplied the
    # figures carries uuids, which hulk writes into Figure.uuid as well as its own row. Either
    # names a figure, so both are offered and a row supplies exactly one.
    match_columns = (("id", "pk"), ("uuid", "uuid"))

    lookups = [
        EnumLookup("role", Figure.ROLE),
        EnumLookup("start_date_accuracy", DATE_ACCURACY),
        EnumLookup("end_date_accuracy", DATE_ACCURACY),
    ]
