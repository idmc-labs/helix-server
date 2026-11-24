from apps.contrib.management.base import (
    BaseImportCommand,
    EnumLookup,
    M2MByName,
    QualifiedFKByName,
)
from apps.country.models import Country
from apps.organization.models import Organization, OrganizationKind
from apps.organization.serializers import OrganizationSerializer, OrganizationUpdateSerializer


class Command(BaseImportCommand):
    help = "Bulk create/update organizations from an .xlsx sheet. Use --make-template to generate a blank template."

    model = Organization
    create_serializer = OrganizationSerializer
    update_serializer = OrganizationUpdateSerializer

    # `parent` is intentionally not exposed for import.
    EXTRA_EXCLUDED_FIELDS = frozenset({"parent"})

    lookups = [
        EnumLookup("category", Organization.ORGANIZATION_CATEGORY),
        # A kind is written "<source type> - <subtype>" (e.g. "Government - Other"): subtype names
        # repeat across types ("Other" is under Government and Civilians).
        QualifiedFKByName(
            "organization_kind",
            OrganizationKind,
            parent_lookup="source_type__name",
            child_lookup="name",
            separator=" - ",
        ),
        # NOTE: Not used because "parent" is in EXTRA_EXCLUDED_FIELDS
        # organization names are not unique, so disambiguating as
        # "<org name> - <country name>"
        QualifiedFKByName(
            "parent",
            Organization,
            parent_lookup="name",
            child_lookup="countries__idmc_short_name",
            separator=" - ",
            list_values=False,
        ),
        M2MByName("countries", Country, "iso3", list_values=False),
    ]
