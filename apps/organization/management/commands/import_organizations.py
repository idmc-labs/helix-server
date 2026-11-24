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
    help = (
        "Bulk create/update organizations from an .xlsx sheet. Use --make-template to generate the template, "
        "prefilled with each organization's id, name and current kind."
    )

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

    def handle(self, *args, **options):
        super().handle(*args, **options)
        if options.get("make_template"):
            self._fill_template(options["make_template"])

    def _fill_template(self, path):
        """Add each organization's id, name and current kind to the Data sheet, in
        the format the import reads back. The other columns stay blank, so importing the sheet back leaves
        them unchanged."""
        from openpyxl import load_workbook

        workbook = load_workbook(path)
        sheet = workbook[self.DATA_SHEET]
        columns = [str(cell.value) for cell in sheet[1]]
        separator = self.lookup_map["organization_kind"].separator
        qs = Organization.objects.order_by("id").values_list(
            "id", "name", "organization_kind__source_type__name", "organization_kind__name"
        )
        for org_id, name, source_type, kind in qs.iterator(chunk_size=2000):
            row = {
                "id": org_id,
                "name": name,
                "organization_kind": f"{source_type}{separator}{kind}" if kind else None,
            }
            sheet.append([row.get(column) for column in columns])
        workbook.save(path)
