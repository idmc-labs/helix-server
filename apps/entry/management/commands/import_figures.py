import typing
from contextlib import contextmanager

from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.management.base import (
    BaseImportCommand,
    EnumLookup,
    FKById,
    FKByName,
)
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.entry.serializers import FigureSerializer
from apps.entry.utils import BulkUpdateFigureManager
from apps.event.models import (
    DisasterSubCategory,
    DisasterSubType,
    Event,
    OsvSubType,
    OtherSubType,
    ViolenceSubType,
)


class Command(BaseImportCommand):
    help = (
        "Bulk update existing figures from an .xlsx sheet. "
        "Use --make-template to generate a blank template. "
        "This importer only updates existing rows (matched by id); it never creates."
    )

    model = Figure
    update_serializer = FigureSerializer
    update_only = True

    # geo_locations and disaggregation_age are nested list serializers, which a single cell cannot
    # hold; locations have their own importer, keyed by FigureLocation id. uuid identifies the
    # figure across systems (hulk matches entities on it), so it is not data an operator edits.
    # entry re-parents the figure rather than editing it.
    #
    # country is left out because the rule that a figure's locations sit inside its country is
    # checked only when locations are sent (FigureSerializer._validate_geo_locations returns early
    # otherwise), and this importer never sends them. event is kept because its own cross-checks,
    # against the event's countries and dates, do run on a partial update.
    #
    # The many-to-many fields are deferred.
    EXTRA_EXCLUDED_FIELDS = frozenset(
        {
            "geo_locations",
            "disaggregation_age",
            "uuid",
            "entry",
            "country",
            "tags",
            "context_of_violence",
            "sources",
        }
    )

    # The sub-type taxonomies are small and their names are unique, so they resolve by name and
    # enumerate into the template. Events are too many to enumerate and their names are not
    # unique, so they are referenced by id.
    lookups = [
        EnumLookup("quantifier", Figure.QUANTIFIER),
        EnumLookup("unit", Figure.UNIT),
        EnumLookup("category", Figure.FIGURE_CATEGORY_TYPES),
        EnumLookup("term", Figure.FIGURE_TERMS),
        EnumLookup("displacement_occurred", Figure.DISPLACEMENT_OCCURRED),
        EnumLookup("role", Figure.ROLE),
        EnumLookup("start_date_accuracy", DATE_ACCURACY),
        EnumLookup("end_date_accuracy", DATE_ACCURACY),
        EnumLookup("figure_cause", Crisis.CRISIS_TYPE),
        FKById("event", Event),
        # error_on_multiple so a name that stops being unique fails the row instead of silently
        # resolving to whichever row was cached first.
        FKByName("violence_sub_type", ViolenceSubType, "name", error_on_multiple=True),
        FKByName("disaster_sub_category", DisasterSubCategory, "name", error_on_multiple=True),
        FKByName("disaster_sub_type", DisasterSubType, "name", error_on_multiple=True),
        FKByName("other_sub_type", OtherSubType, "name", error_on_multiple=True),
        FKByName("osv_sub_type", OsvSubType, "name", error_on_multiple=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bulk_manager: typing.Optional[BulkUpdateFigureManager] = None

    def serializer_context(self, request) -> typing.Dict:
        context = super().serializer_context(request)
        context["bulk_manager"] = self._bulk_manager
        return context

    @contextmanager
    def import_context(self):
        """
        FigureSerializer records each touched event on a bulk manager and, on exit, recomputes those
        events' review status from their figures. Without it every event the import touched is left
        with a stale status, so the run is wrapped the way the bulk figure mutation wraps its own.
        """
        with BulkUpdateFigureManager() as bulk_manager:
            self._bulk_manager = bulk_manager
            try:
                yield
            finally:
                self._bulk_manager = None
