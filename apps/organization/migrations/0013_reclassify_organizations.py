"""Move every organization from its old kind to the new subtype (from 0012) the old kind maps to,
then remove the old kinds.

Forward-only: going back does not bring the old kinds back, the organizations stay on the new subtypes.
Fails, changing nothing, if an organization is on an old kind that OLD_KIND_TO_SUBTYPE does not map.
Organizations with no kind are left as they are.
"""

import re

from django.db import migrations

# Old kind name -> (type name, subtype name).
OLD_KIND_TO_SUBTYPE = {
    "Media": ("Media", "Media"),
    "Government": ("Government", "National Government"),
    "Civil Society": ("Civilians", "National NGOs and Associations"),
    "National/Regional Disaster Authority": ("Government", "Disaster Agencies"),
    "United Nations": ("United Nations", "United Nations"),
    "Local Authority": ("Government", "Local Authorities"),
    "International Organisations": ("International Organisations", "Intergovernmental Organisations"),
    "International NGOs": ("International NGOs", "International NGOs"),
    "Red Cross/Red Crescent Movement": ("International Organisations", "Red Cross/Red Crescent"),
    "Other": ("Other", "Unclassified"),
    "Clusters and Consortias": ("International Organisations", "Clusters and Consortia"),
    "Private Sector": ("Other", "Private Sector"),
    "Community Leaders": ("Civilians", "Community Leaders"),
    "Academia": ("Civilians", "Academic and Research Institutions"),
    "Non-State Armed Group": ("Other", "Non-State Armed Group"),
    "Affected population": ("Civilians", "Affected Population"),
}


def _key(name):
    # Ignore case, and non-breaking or repeated spaces, in kind names.
    return re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip().casefold()


def reclassify_organizations(apps, schema_editor):
    Organization = apps.get_model("organization", "Organization")
    OrganizationKind = apps.get_model("organization", "OrganizationKind")

    subtypes = {
        (_key(kind.source_type.name), _key(kind.name)): kind
        for kind in OrganizationKind.objects.filter(source_type__isnull=False).select_related("source_type")
    }
    mapping = {_key(old): (_key(type_name), _key(subtype)) for old, (type_name, subtype) in OLD_KIND_TO_SUBTYPE.items()}

    problems = []
    moves = []
    for old_kind in OrganizationKind.objects.filter(source_type__isnull=True).order_by("name"):
        #NOTE: Archived organizations included
        if not Organization.objects.filter(organization_kind=old_kind).exists():
            continue
        target = mapping.get(_key(old_kind.name))
        if target is None:
            problems.append(f"old kind {old_kind.name!r} is not in OLD_KIND_TO_SUBTYPE")
        elif target not in subtypes:
            problems.append(f"old kind {old_kind.name!r} maps to a subtype that does not exist: {target}")
        else:
            moves.append((old_kind, subtypes[target]))

    if problems:
        raise RuntimeError("Organizations not reclassified, nothing changed:\n- " + "\n- ".join(problems))

    for old_kind, new_kind in moves:
        Organization.objects.filter(organization_kind=old_kind).update(organization_kind=new_kind)

    # Every old kind is now unused (PROTECT refuses the delete otherwise).
    OrganizationKind.objects.filter(source_type__isnull=True).delete()

    # NOTE: Next migration alters the organization kind table in the same transaction. Postgres refuses to ALTER a
    # table with pending (deferred) foreign-key checks, so run them now.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")

class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0012_source_type"),
    ]
    operations = [
        migrations.RunPython(reclassify_organizations, migrations.RunPython.noop),
    ]
