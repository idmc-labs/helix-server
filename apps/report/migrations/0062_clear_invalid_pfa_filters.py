from django.db import migrations

# Mirrors apps.report.serializers.PFA_ALLOWED_FILTERS, frozen at this migration.
PFA_ALLOWED_FILTERS = {
    "filter_figure_start_after",
    "filter_figure_end_before",
    "filter_figure_countries",
    "filter_figure_crisis_types",
    "filter_figure_categories",
    "filter_figure_roles",
}


def clear_invalid_pfa_filters(apps, schema_editor):
    """Clear filters a PFA report may not carry.

    A PFA total is defined by year, country, cause and category; the generation aggregates on
    exactly those. Reports carrying more were narrowing a published figure by a dimension the
    aggregate never applied, so the stored filters are wrong rather than meaningful. Clearing them
    keeps the report visible in GIDD, where rejecting it would silently drop it.
    """
    Report = apps.get_model("report", "Report")
    names = [
        field.name
        for field in Report._meta.get_fields()
        if getattr(field, "many_to_many", False)
        and field.name.startswith("filter_")
        and field.name not in PFA_ALLOWED_FILTERS
    ]
    for report in Report.objects.filter(is_pfa_visible_in_gidd=True).iterator():
        for name in names:
            getattr(report, name).clear()


class Migration(migrations.Migration):
    dependencies = [("report", "0061_report_report_created_at_desc_idx")]
    operations = [migrations.RunPython(clear_invalid_pfa_filters, migrations.RunPython.noop)]
