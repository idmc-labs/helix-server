"""No nested list may hand back a whole Event/Crisis/Entry/Figure/Report/Organization/ExtractionQuery set.

These seven carry the heaviest rows and the widest reverse fan-out in the schema, so a list
field over them with no page argument is a request the caller cannot bound and the server
cannot refuse: `disasterCategoryList{results{figures}}` was 22.8s and 125,113 Figure
instances before it was dropped, and one organization publishes 3321 entries.

The bound lives in each type's `exclude_fields`, which is easy to forget when a model gains
a relation -- `RelationBatchedDjangoObjectType` exposes reverse relations automatically, so
a new unbounded list appears by default rather than on purpose. This reads the committed
schema instead of the wiring, so it fails for a field added through any route.

To add a genuinely bounded field, give it `pageSize` (see `DjangoPaginatedListObjectField`);
if it is bounded by something other than pagination, name it in ALLOWED with why.
"""

import pathlib
import re

from django.test import SimpleTestCase

HEAVY_TYPES = {
    "EventType",
    "CrisisType",
    "EntryType",
    "FigureType",
    "ReportType",
    "OrganizationType",
    "ExtractionQueryObjectType",
}

# Bounded by the caller's own input rather than by paging, with the measured worst case on
# the production-shaped dump.
ALLOWED = {
    # A report's hand-picked filter selections, rendered as filter chips (max 57 events, 1 crisis,
    # 0 sources, 0 publishers over 2800 reports).
    "ReportType.filterFigureEvents",
    "ReportType.filterFigureCrises",
    "ReportType.filterFigureSources",
    "ReportType.filterEntryPublishers",
    # The same selections on a saved extraction query (max 2 sources, 17 publishers over 23 queries).
    "ExtractionQueryObjectType.filterFigureEvents",
    "ExtractionQueryObjectType.filterFigureCrises",
    "ExtractionQueryObjectType.filterFigureSources",
    "ExtractionQueryObjectType.filterEntryPublishers",
    # Attribution on a single row, bounded by how many organizations one document names
    # (max 10 publishers on an entry, 24 sources on a figure, 15 publishers and 19 sources on a
    # contextual update).
    "EntryType.publishers",
    "FigureType.sources",
    "ContextualUpdateType.sources",
    "ContextualUpdateType.publishers",
    # A mutation echoing back the rows the request itself submitted.
    "BulkUpdateFigures.result",
    "BulkUpdateFigures.deletedResult",
}

SCHEMA = pathlib.Path(__file__).resolve().parents[3] / "schema.graphql"


def unbounded_heavy_lists():
    """Every list-returning field of a heavy type in the committed schema that takes no `pageSize`."""
    text = SCHEMA.read_text()
    found = []
    for type_name, body in re.findall(r"type (\w+) \{(.*?)\n\}", text, re.S):
        # `XListType.results` is the page of an already-paginated list, not a field a caller reaches past.
        if type_name.endswith("ListType"):
            continue
        for line in body.splitlines():
            match = re.match(r"(\w+)(\([^)]*\))?:\s*(.+)$", line.strip())
            if not match:
                continue
            field, args, returns = match.group(1), match.group(2) or "", match.group(3)
            base = returns.replace("!", "").replace("[", "").replace("]", "")
            listy = "[" in returns or base.endswith("ListType")
            heavy = base in HEAVY_TYPES or base in {f"{name[:-4]}ListType" for name in HEAVY_TYPES}
            if listy and heavy and "pageSize" not in args:
                found.append(f"{type_name}.{field}")
    return found


class TestNoUnboundedEntityLists(SimpleTestCase):
    def test_schema_snapshot_is_present(self):
        # The scan silently passes if the path is wrong, so pin that it read the real schema.
        self.assertTrue(SCHEMA.is_file(), f"{SCHEMA} not found")
        self.assertIn("type FigureType", SCHEMA.read_text())

    def test_no_heavy_list_is_reachable_without_a_page_argument(self):
        offenders = sorted(set(unbounded_heavy_lists()) - ALLOWED)
        self.assertEqual(
            offenders,
            [],
            "these expose a whole heavy-entity set with no page argument; "
            "paginate them, exclude them, or justify them in ALLOWED",
        )

    def test_allowed_entries_still_exist(self):
        # An exemption for a field that has since been renamed or dropped would quietly widen
        # the bound.
        stale = sorted(ALLOWED - set(unbounded_heavy_lists()))
        self.assertEqual(stale, [], "these ALLOWED entries no longer match a schema field")
