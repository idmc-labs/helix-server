from collections import OrderedDict

from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.management.base import BaseImportCommand, EnumLookup
from apps.contrib.serializers import MetaInformationSerializerMixin
from apps.entry.models import Figure


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
        # The one rule wholly about the fields being edited. Checked against the row as it will
        # end up, so a sheet that moves only start_date cannot step past a stored end_date.
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and start_date > end_date:
            raise ValidationError(OrderedDict({"start_date": f"{start_date} is after end_date {end_date}"}))
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
