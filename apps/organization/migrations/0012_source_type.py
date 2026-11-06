import apps.organization.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_enumfield.db.fields

# (level, type, subtypes). A type with a single subtype names it after the type.
SOURCE_TYPE_TAXONOMY = [
    (
        1,
        "Government",
        [
            "IDP Specific Institutions",
            "National Government",
            "Sub-national Government",
            "Local Authorities",
            "Disaster Agencies",
            "Other",
        ],
    ),
    (1, "United Nations", ["United Nations"]),
    (
        1,
        "International Organisations",
        [
            "Clusters and Consortia",
            "Intergovernmental Organisations",
            "Red Cross/Red Crescent",
        ],
    ),
    (2, "International NGOs", ["International NGOs"]),
    (
        2,
        "Civilians",
        [
            "National NGOs and Associations",
            "Academic and Research Institutions",
            "Community Leaders",
            "Affected Population",
            "Other",
        ],
    ),
    (3, "Media", ["Media"]),
    (3, "Other", ["Private Sector", "Non-State Armed Group", "Unclassified"]),
]

# NOTE: the new kinds also get the matching old OrganizationKind.reliability (LOW=0, MEDIUM=1, HIGH=2),
# so the deprecated sourcesReliability field stays consistent. Not needed once reliability is
# removed.

LEVEL_TO_RELIABILITY = {1: 2, 2: 1, 3: 0}



def insert_source_types(apps, schema_editor):
    SourceType = apps.get_model("organization", "SourceType")
    OrganizationKind = apps.get_model("organization", "OrganizationKind")

    for level, type_name, subtype_names in SOURCE_TYPE_TAXONOMY:
        source_type, _ = SourceType.objects.get_or_create(name=type_name, defaults={"level": level})
        for subtype_name in subtype_names:
            # Matched on (name, type): "Other" is a subtype of both Government and Civilians.
            OrganizationKind.objects.get_or_create(
                name=subtype_name,
                source_type=source_type,
                defaults={"reliability": LEVEL_TO_RELIABILITY[level]},
            )

    # NOTE: Django creates the source_type index after this step, in the same transaction. Postgres
    # refuses to ALTER a table with pending (deferred) foreign-key checks, so run them now.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def remove_source_types(apps, schema_editor):
    SourceType = apps.get_model("organization", "SourceType")
    OrganizationKind = apps.get_model("organization", "OrganizationKind")

    type_names = [type_name for _, type_name, _ in SOURCE_TYPE_TAXONOMY]
    # PROTECT on Organization.organization_kind refuses this if an organization already uses a subtype.
    OrganizationKind.objects.filter(source_type__name__in=type_names).delete()
    SourceType.objects.filter(name__in=type_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organization', '0011_auto_20260225_0529'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='organization_kind',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='organizations', to='organization.organizationkind', verbose_name='Organization Type'),
        ),
        migrations.CreateModel(
            name='SourceType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_id', models.CharField(blank=True, max_length=32, null=True, verbose_name='Old primary key')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified At')),
                ('version_id', models.CharField(blank=True, max_length=16, null=True, verbose_name='Version')),
                ('name', models.CharField(max_length=256, verbose_name='Name')),
                ('level', django_enumfield.db.fields.EnumField(enum=apps.organization.models.SourceType.SOURCE_TYPE_CLASSIFICATION)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_sourcetype', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('last_modified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By')),
            ],
            options={
                'ordering': ['level', 'name'],
            },
        ),
        migrations.AddField(
            model_name='organizationkind',
            name='source_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='organization_kinds', to='organization.sourcetype', verbose_name='Source type'),
        ),
        migrations.RunPython(insert_source_types, remove_source_types),
    ]
