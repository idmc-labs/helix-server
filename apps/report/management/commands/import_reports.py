from apps.contrib.management.base import (
    BaseImportCommand,
    EnumArrayLookup,
    M2MById,
    M2MByName,
)
from apps.contrib.serializers import IntegerIDField, UpdateSerializerMixin
from apps.country.models import Country, CountryRegion, GeographicalGroup
from apps.crisis.models import Crisis
from apps.entry.models import Figure, FigureTag
from apps.event.models import (
    DisasterCategory,
    DisasterSubCategory,
    DisasterSubType,
    DisasterType,
    Event,
    Violence,
    ViolenceSubType,
)
from apps.report.models import Report
from apps.report.serializers import ReportSerializer


class ReportImportSerializer(ReportSerializer):
    """Report fields an operator may write from a sheet.

    `is_pfa_visible_in_gidd` is writable here but not on `ReportSerializer`, whose fields become the
    report mutation inputs: the GraphQL surface gates the flag behind `setPfaVisibleInGidd` and its
    own admin permission, which a field on the create/update inputs would bypass.
    """

    class Meta(ReportSerializer.Meta):
        fields = ReportSerializer.Meta.fields + ["is_pfa_visible_in_gidd"]


class ReportImportUpdateSerializer(UpdateSerializerMixin, ReportImportSerializer):
    id = IntegerIDField(required=True)


class Command(BaseImportCommand):
    help = (
        "Bulk create/update reports from an .xlsx sheet. "
        "Use --make-template to generate a blank template. "
        "Note: updating an existing report requires --user-email of a user permitted to edit it."
    )

    model = Report
    create_serializer = ReportImportSerializer
    update_serializer = ReportImportUpdateSerializer
    lookups = [
        # Enum arrays
        EnumArrayLookup("filter_figure_categories", Figure.FIGURE_CATEGORY_TYPES),
        EnumArrayLookup("filter_figure_crisis_types", Crisis.CRISIS_TYPE),
        EnumArrayLookup("filter_figure_roles", Figure.ROLE),
        # Flat many-to-many relations.
        M2MByName("filter_figure_regions", CountryRegion, "name"),
        M2MByName("filter_figure_countries", Country, "iso3", list_values=False),
        M2MByName("filter_figure_geographical_groups", GeographicalGroup, "name"),
        M2MByName("filter_figure_tags", FigureTag, "name"),
        M2MByName("filter_figure_violence_types", Violence, "name"),
        M2MByName("filter_figure_disaster_categories", DisasterCategory, "name"),
        M2MByName("filter_figure_disaster_sub_categories", DisasterSubCategory, "name"),
        M2MByName("filter_figure_disaster_types", DisasterType, "name"),
        M2MByName("filter_figure_disaster_sub_types", DisasterSubType, "name"),
        M2MByName("filter_figure_violence_sub_types", ViolenceSubType, "name"),
        # High-cardinality tables (crises, events) are referenced by id, not by (non-unique) name.
        M2MById("filter_figure_crises", Crisis),
        M2MById("filter_figure_events", Event),
    ]
