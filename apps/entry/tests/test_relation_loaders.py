"""Regression coverage for the dataloader-engine + queryset-factory-flip work.

dataloader-engine swapped 16 type modules to ``RelationBatchedDjangoObjectType``, which
auto-wires loader-backed resolvers for relation fields WITHOUT an explicit resolver:
  - forward FK / OneToOne          -> RelationNodeLoader        (_make_fk_resolver)
  - reverse-FK / M2M (plain List)  -> ReverseFKListLoader / M2MListLoader (_make_list_resolver)
  - reverse OneToOne                -> ReverseOneToOneLoader     (_make_reverse_o2o_resolver)
queryset-factory-flip then made ``DjangoPaginatedListObjectField.get_queryset`` return a
plain queryset (relations are served by the loaders at ANY depth, not by
graphene_django_extras.queryset_factory which only reached the first level under a list).

These tests assert those changes are BEHAVIOUR-PRESERVING: every relation shape resolves to
the correct value, at depth, with no per-parent (N+1) query fan-out — plus a structural guard
that every auto-wired field across the whole schema still routes through the loader module.
"""

import json
from collections import defaultdict

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    CrisisFactory,
    EntryFactory,
    EventCodeFactory,
    EventFactory,
    FigureFactory,
    MonitoringSubRegionFactory,
    OrganizationFactory,
    OrganizationKindFactory,
    ParkingLotFactory,
    TagFactory,
    UnifiedReviewCommentFactory,
    UserFactory,
    ViolenceFactory,
)
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestRelationLoaderEngine(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.admin)

    def _run(self, query, variables=None):
        response = self.query(query, variables=variables)
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]

    def _figure(self, **kwargs):
        # Figure.event is a NOT NULL FK, so every figure needs an event.
        kwargs.setdefault("event", EventFactory.create())
        return FigureFactory.create(**kwargs)

    # ------------------------------------------------------------------ #
    # Forward FK / OneToOne  ->  RelationNodeLoader
    # ------------------------------------------------------------------ #
    def test_forward_fk_resolves_correct_object(self) -> None:
        entry = EntryFactory.create()
        event = EventFactory.create()
        country = CountryFactory.create()
        figure = self._figure(entry=entry, event=event, country=country)

        data = self._run(
            """
            query { figureList(ordering: "id") { results {
              id event { id } entry { id } country { id }
            } } }
            """
        )
        row = next(r for r in data["figureList"]["results"] if r["id"] == str(figure.id))
        self.assertEqual(row["event"]["id"], str(event.id))
        self.assertEqual(row["entry"]["id"], str(entry.id))
        self.assertEqual(row["country"]["id"], str(country.id))

    def test_nullable_fk_null_when_unset_and_value_when_set(self) -> None:
        violence = ViolenceFactory.create()
        with_v = self._figure(violence=violence)
        without_v = self._figure(violence=None)

        data = self._run('query { figureList(ordering: "id") { results { id violence { id } } } }')
        by_id = {r["id"]: r["violence"] for r in data["figureList"]["results"]}
        self.assertEqual(by_id[str(with_v.id)]["id"], str(violence.id))
        self.assertIsNone(by_id[str(without_v.id)])

    def test_created_by_fk(self) -> None:
        author = UserFactory.create()
        figure = self._figure(created_by=author)
        data = self._run('query { figureList(ordering: "id") { results { id createdBy { id } } } }')
        row = next(r for r in data["figureList"]["results"] if r["id"] == str(figure.id))
        self.assertEqual(row["createdBy"]["id"], str(author.id))

    def test_self_fk_organization_parent(self) -> None:
        parent = OrganizationFactory.create()
        child = OrganizationFactory.create(parent=parent)
        data = self._run('query { organizationList(ordering: "id") { results { id parent { id } } } }')
        by_id = {r["id"]: r["parent"] for r in data["organizationList"]["results"]}
        self.assertEqual(by_id[str(child.id)]["id"], str(parent.id))
        self.assertIsNone(by_id[str(parent.id)])

    def test_forward_o2o_entry_associated_parked_item(self) -> None:
        parked = ParkingLotFactory.create()
        entry = EntryFactory.create(associated_parked_item=parked)
        EntryFactory.create()  # a second entry with no parked item -> null
        data = self._run(
            """
            query { entryList(ordering: "id") { results {
              id associatedParkedItem { id }
            } } }
            """
        )
        row = next(r for r in data["entryList"]["results"] if r["id"] == str(entry.id))
        self.assertEqual(row["associatedParkedItem"]["id"], str(parked.id))

    # ------------------------------------------------------------------ #
    # Reverse OneToOne  ->  ReverseOneToOneLoader
    # ------------------------------------------------------------------ #
    def test_reverse_o2o_resolves_correct_object(self) -> None:
        parked = ParkingLotFactory.create()
        entry = EntryFactory.create(associated_parked_item=parked)
        orphan = ParkingLotFactory.create()  # no entry points back -> null

        data = self._run("query { parkedItemList { results { id entry { id } } } }")
        by_id = {r["id"]: r["entry"] for r in data["parkedItemList"]["results"]}
        self.assertEqual(by_id[str(parked.id)]["id"], str(entry.id))
        self.assertIsNone(by_id[str(orphan.id)])

    # ------------------------------------------------------------------ #
    # Reverse-FK list  ->  ReverseFKListLoader
    # ------------------------------------------------------------------ #
    def test_reverse_fk_list_country_parked_items(self) -> None:
        # CountryType.parkedItems (ParkedItem.country) is a plain, non-paginated reverse-FK list,
        # so it resolves through ReverseFKListLoader rather than a paginated field's queryset.
        country = CountryFactory.create()
        item_a = ParkingLotFactory.create(country=country)
        item_b = ParkingLotFactory.create(country=country)
        empty_country = CountryFactory.create()

        data = self._run('query { countryList(ordering: "id") { results { id parkedItems { id } } } }')
        by_id = {r["id"]: {p["id"] for p in r["parkedItems"]} for r in data["countryList"]["results"]}
        self.assertEqual(by_id[str(country.id)], {str(item_a.id), str(item_b.id)})
        self.assertEqual(by_id[str(empty_country.id)], set())

    def test_sibling_reverse_fk_fields_sharing_child_fk_name_stay_separate(self) -> None:
        # EventType exposes two reverse-FK lists whose child FKs are both named `event`:
        # eventCodes (EventCode.event) and eventReviews (UnifiedReviewComment.event). A loader
        # cache ref keyed only by the FK field name collapses them into ONE per-request loader,
        # so whichever field resolves second gets the other model's rows.
        event = EventFactory.create()
        code = EventCodeFactory.create(event=event)
        review = UnifiedReviewCommentFactory.create(event=event, created_by=self.admin)

        data = self._run(
            """
            query { eventList(ordering: "id") { results {
              id eventCodes { id } eventReviews { id }
            } } }
            """
        )
        row = next(r for r in data["eventList"]["results"] if r["id"] == str(event.id))
        self.assertEqual({c["id"] for c in row["eventCodes"]}, {str(code.id)})
        self.assertEqual({r["id"] for r in row["eventReviews"]}, {str(review.id)})

    # ------------------------------------------------------------------ #
    # M2M list  ->  M2MListLoader
    # ------------------------------------------------------------------ #
    def test_m2m_list_figure_tags(self) -> None:
        tag_a = TagFactory.create()
        tag_b = TagFactory.create()
        tagged = self._figure()
        tagged.tags.add(tag_a, tag_b)
        untagged = self._figure()

        data = self._run('query { figureList(ordering: "id") { results { id tags { id } } } }')
        by_id = {r["id"]: {t["id"] for t in r["tags"]} for r in data["figureList"]["results"]}
        self.assertEqual(by_id[str(tagged.id)], {str(tag_a.id), str(tag_b.id)})
        self.assertEqual(by_id[str(untagged.id)], set())

    # ------------------------------------------------------------------ #
    # queryset-factory-flip: FK resolves BEYOND the first level under a list
    # (queryset_factory only reached level 1; the loader reaches any depth)
    # ------------------------------------------------------------------ #
    def test_flip_depth_two_fk_resolves(self) -> None:
        # figure.event.violence is a 2-level forward-FK chain under figureList.
        event = EventFactory.create()  # EventFactory sets a violence SubFactory
        figure = self._figure(event=event)
        self.assertIsNotNone(event.violence_id)

        data = self._run(
            """
            query { figureList(ordering: "id") { results {
              id event { id violence { id } }
            } } }
            """
        )
        row = next(r for r in data["figureList"]["results"] if r["id"] == str(figure.id))
        self.assertEqual(row["event"]["id"], str(event.id))
        self.assertEqual(row["event"]["violence"]["id"], str(event.violence_id))

    # ------------------------------------------------------------------ #
    # N+1 guards: per-parent query count must stay flat as parents grow
    # ------------------------------------------------------------------ #
    def _query_count(self, query) -> int:
        with CaptureQueriesContext(connection) as ctx:
            self._run(query)
        return len(ctx.captured_queries)

    def test_forward_fk_and_depth_have_no_n_plus_1(self) -> None:
        from apps.entry.models import Figure

        query = """
            query { figureList(ordering: "id") { results {
              id event { id violence { id } } entry { id } country { id } createdBy { id }
            } } }
        """
        author = UserFactory.create()
        Figure.objects.all().delete()
        self._figure(created_by=author)
        one = self._query_count(query)

        self._figure(created_by=author)
        self._figure(created_by=author)
        many = self._query_count(query)

        self.assertEqual(
            one,
            many,
            f"forward-FK/depth resolution scales with row count (N+1): {one} q for 1 figure vs {many} for 3.",
        )

    def test_reverse_and_m2m_have_no_n_plus_1(self) -> None:
        from apps.entry.models import Figure

        query = 'query { figureList(ordering: "id") { results { id tags { id } contextOfViolence { id } } } }'
        Figure.objects.all().delete()
        f1 = self._figure()
        f1.tags.add(TagFactory.create())
        one = self._query_count(query)

        f2 = self._figure()
        f2.tags.add(TagFactory.create())
        self._figure()
        many = self._query_count(query)

        self.assertEqual(
            one,
            many,
            f"reverse-FK/M2M list resolution scales with row count (N+1): {one} q for 1 figure vs {many} for 3.",
        )

    def test_reverse_o2o_has_no_n_plus_1(self) -> None:
        # A OneToOneRel matches none of the other auto-wire branches (concrete=False,
        # one_to_many=False, many_to_many=False), so it used to get no loader and fell back
        # to the descriptor: one query per parent row.
        from apps.parking_lot.models import ParkedItem

        query = "query { parkedItemList { results { id entry { id } } } }"
        ParkedItem.objects.all().delete()
        EntryFactory.create(associated_parked_item=ParkingLotFactory.create())
        one = self._query_count(query)

        EntryFactory.create(associated_parked_item=ParkingLotFactory.create())
        ParkingLotFactory.create()  # no entry -> the loader must still not fan out
        many = self._query_count(query)

        self.assertEqual(
            one,
            many,
            f"reverse-O2O resolution scales with row count (N+1): {one} q for 1 parked item vs {many} for 3.",
        )

    # ------------------------------------------------------------------ #
    # Structural guard: every auto-wired relation field across the whole
    # schema still routes through the relation-loader module (catches a type
    # silently reverting off RelationBatchedDjangoObjectType).
    # ------------------------------------------------------------------ #
    def test_all_autowired_fields_route_through_loaders(self) -> None:
        # Force the whole schema to load so every RelationBatchedDjangoObjectType subclass is
        # registered (else __subclasses__() is empty when this test runs before any query).
        import helix.schema  # noqa: F401
        from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType

        def all_subclasses(cls):
            found = set()
            for sub in cls.__subclasses__():
                found.add(sub)
                found |= all_subclasses(sub)
            return found

        types = [
            c for c in all_subclasses(RelationBatchedDjangoObjectType) if getattr(getattr(c, "_meta", None), "model", None)
        ]
        self.assertGreater(len(types), 30, "engine base class adoption dropped unexpectedly")

        fk_count = list_count = 0
        for cls in types:
            for name in list(cls._meta.fields.keys()):
                resolver = getattr(cls, "resolve_%s" % name, None)
                if resolver is None or "relation_loaders" not in getattr(resolver, "__module__", ""):
                    continue
                qual = getattr(resolver, "__qualname__", "")
                if "_make_fk_resolver" in qual:
                    fk_count += 1
                elif "_make_list_resolver" in qual:
                    list_count += 1

        # Floors, not exact counts: legitimate additions must not fail, while a drop means a
        # type lost the auto-wiring base.
        # `GiddReleaseMetadataType` pins `Meta.fields`, which drops its `modified_by` resolver:
        # that FK is how an unauthenticated caller reached `UserType`.
        self.assertGreaterEqual(fk_count, 125, "auto-wired forward-FK resolvers regressed")
        # The four `legacy_disasters` reverses count, because `DisasterLegacy` is retained; the
        # two gidd_* reverses do not, because `CountryType` excludes them rather than exposing
        # them unpaginated.
        self.assertGreaterEqual(list_count, 83, "auto-wired reverse-FK/M2M resolvers regressed")

        # Spot-check critical FigureType fields are loader-wired by name.
        from apps.entry.schema import FigureType

        for field in ("event", "entry", "country", "created_by", "violence"):
            resolver = getattr(FigureType, "resolve_%s" % field, None)
            self.assertTrue(
                resolver is not None and "relation_loaders" in getattr(resolver, "__module__", ""),
                f"FigureType.{field} is not loader-wired",
            )

    def test_no_reverse_o2o_field_is_left_unwired(self) -> None:
        # The bug class: a relation kind the auto-wire has no branch for gets NO loader and
        # degrades silently to one query per row. Walk every exposed reverse-O2O field in the
        # schema rather than naming the two known ones, so a newly added one cannot slip back in.
        from graphene_django_extras.utils import to_snake_case

        import helix.schema  # noqa: F401
        from utils.graphene.fields import DjangoPaginatedListObjectField
        from utils.graphene.relation_loaders import RelationBatchedDjangoObjectType

        def all_subclasses(cls):
            found = set()
            for sub in cls.__subclasses__():
                found.add(sub)
                found |= all_subclasses(sub)
            return found

        wired, unwired = [], []
        for cls in all_subclasses(RelationBatchedDjangoObjectType):
            model = getattr(getattr(cls, "_meta", None), "model", None)
            if model is None:
                continue
            rels = {f.name: f for f in model._meta.get_fields() if f.is_relation}
            for name in list(cls._meta.fields.keys()):
                snake = to_snake_case(name)
                rel = rels.get(snake) or rels.get(name)
                if rel is None or isinstance(cls._meta.fields.get(name), DjangoPaginatedListObjectField):
                    continue
                if not (getattr(rel, "one_to_one", False) and not getattr(rel, "concrete", False)):
                    continue
                resolver = getattr(cls, "resolve_%s" % snake, None)
                target = wired if "_make_reverse_o2o_resolver" in getattr(resolver, "__qualname__", "") else unwired
                target.append("%s.%s" % (cls.__name__, name))

        self.assertFalse(unwired, "reverse-O2O fields with no batching loader (one query per row): %r" % unwired)
        # CountryType.portfolio + ParkedItemType.entry + the 5 hulk entity back-references.
        self.assertGreaterEqual(len(wired), 7, "reverse-O2O field walk shrank unexpectedly")
        self.assertIn("CountryType.portfolio", wired)
        self.assertIn("ParkedItemType.entry", wired)

    def test_relation_list_loader_refs_are_collision_free(self) -> None:
        # Two fields resolving DIFFERENT relations must never share a loader cache ref: refs key
        # the per-request loader cache, so a shared ref means one loader serves both fields and
        # whichever resolves second gets the other model's rows (the eventCodes/eventReviews bug).
        from graphene_django_extras.utils import to_snake_case

        import helix.schema  # noqa: F401
        from utils.graphene.fields import DjangoPaginatedListObjectField
        from utils.graphene.relation_loaders import (
            RelationBatchedDjangoObjectType,
            ReverseFKListLoader,
            _list_loader_factory_for,
        )

        def all_subclasses(cls):
            found = set()
            for sub in cls.__subclasses__():
                found.add(sub)
                found |= all_subclasses(sub)
            return found

        ref_to_specs = defaultdict(set)
        checked = 0
        for cls in all_subclasses(RelationBatchedDjangoObjectType):
            model = getattr(getattr(cls, "_meta", None), "model", None)
            if model is None:
                continue
            rels = {f.name: f for f in model._meta.get_fields() if f.is_relation}
            for name in list(cls._meta.fields.keys()):
                snake = to_snake_case(name)
                rel = rels.get(snake) or rels.get(name)
                if rel is None:
                    continue
                if isinstance(cls._meta.fields.get(name), DjangoPaginatedListObjectField):
                    continue
                if not (getattr(rel, "one_to_many", False) or getattr(rel, "many_to_many", False)):
                    continue
                spec_pair = _list_loader_factory_for(model, rel)
                if spec_pair is None:
                    continue
                ref, factory = spec_pair
                loader = factory()
                if isinstance(loader, ReverseFKListLoader):
                    spec = ("rfk", loader.child_model._meta.label, loader.fk_name)
                else:
                    spec = ("m2m", loader.through._meta.label, loader.source_fk, loader.target_fk)
                ref_to_specs[ref].add(spec)
                checked += 1

        self.assertGreaterEqual(checked, 83, "list-relation field walk shrank unexpectedly")
        collisions = {ref: specs for ref, specs in ref_to_specs.items() if len(specs) > 1}
        self.assertFalse(
            collisions,
            "loader cache refs shared by distinct relations (fields would swap rows): %r" % collisions,
        )

    def test_deduped_bespoke_loaders_now_route_through_generic_loaders(self) -> None:
        # The 8 pure-traversal loaders were deleted; these fields now use the generic loaders.
        # 7 via auto-wire; event_codes is wired explicitly in the class body via
        # reverse_fk_list_resolver (the field name does not match the model reverse accessor).
        import helix.schema  # noqa: F401
        from apps.country.schema import MonitoringSubRegionType
        from apps.entry.schema import EntryType, FigureType
        from apps.event.schema import EventType
        from apps.organization.schema import OrganizationType

        loader_wired = [
            (FigureType, "entry"),  # was FigureEntryLoader
            (EntryType, "document"),  # was EntryDocumentLoader
            (EntryType, "preview"),  # was EntryPreviewLoader
            (EventType, "crisis"),  # was EventCrisisLoader
            (OrganizationType, "organization_kind"),  # was OrganizationOrganizationKindLoader
            (OrganizationType, "countries"),  # was OrganizationCountriesLoader (M2M)
            (MonitoringSubRegionType, "countries"),  # was MonitoringSubRegionCountryLoader
            (EventType, "event_codes"),  # was EventCodeLoader; explicit reverse_fk_list_resolver
        ]
        for cls, field in loader_wired:
            resolver = getattr(cls, "resolve_%s" % field, None)
            self.assertTrue(
                resolver is not None and "relation_loaders" in getattr(resolver, "__module__", ""),
                f"{cls.__name__}.{field} (formerly a bespoke loader) is not wired to a generic loader",
            )


class TestDedupedLoaderBehaviour(HelixGraphQLTestCase):
    """Value-equivalence for the fields whose bespoke loaders were deleted (generic-loader dedup):
    the resolved value must match what the removed loader would have returned."""

    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(self.admin)

    def _run(self, query):
        response = self.query(query)
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]

    def test_event_crisis_fk(self) -> None:  # was EventCrisisLoader -> RelationNodeLoader
        crisis = CrisisFactory.create()
        event = EventFactory.create(crisis=crisis)
        data = self._run('query { eventList(ordering: "id") { results { id crisis { id } } } }')
        row = next(r for r in data["eventList"]["results"] if r["id"] == str(event.id))
        self.assertEqual(row["crisis"]["id"], str(crisis.id))

    def test_organization_kind_fk_and_countries_m2m(self) -> None:
        # was OrganizationOrganizationKindLoader (FK) + OrganizationCountriesLoader (M2M)
        kind = OrganizationKindFactory.create()
        country = CountryFactory.create()
        org = OrganizationFactory.create(organization_kind=kind)
        org.countries.add(country)
        no_kind = OrganizationFactory.create()  # null FK + empty M2M

        data = self._run(
            """
            query { organizationList(ordering: "id") { results {
              id organizationKind { id } countries { id }
            } } }
            """
        )
        by_id = {r["id"]: r for r in data["organizationList"]["results"]}
        self.assertEqual(by_id[str(org.id)]["organizationKind"]["id"], str(kind.id))
        self.assertEqual({c["id"] for c in by_id[str(org.id)]["countries"]}, {str(country.id)})
        self.assertIsNone(by_id[str(no_kind.id)]["organizationKind"])
        self.assertEqual(by_id[str(no_kind.id)]["countries"], [])

    def test_monitoring_sub_region_countries_reverse_fk(self) -> None:
        # was MonitoringSubRegionCountryLoader; the field is a graphene.Dynamic -> verify the
        # auto-wire binds through Dynamic resolution (the flagged risk).
        sub_region = MonitoringSubRegionFactory.create()
        c1 = CountryFactory.create(monitoring_sub_region=sub_region)
        c2 = CountryFactory.create(monitoring_sub_region=sub_region)
        empty_sr = MonitoringSubRegionFactory.create()

        data = self._run('query { monitoringSubRegionList(ordering: "id") { results { id countries { id } } } }')
        by_id = {r["id"]: {c["id"] for c in r["countries"]} for r in data["monitoringSubRegionList"]["results"]}
        self.assertEqual(by_id[str(sub_region.id)], {str(c1.id), str(c2.id)})
        self.assertEqual(by_id[str(empty_sr.id)], set())

    def test_event_codes_thin_reverse_fk(self) -> None:  # was EventCodeLoader -> generic ReverseFKListLoader
        event = EventFactory.create()
        ec1 = EventCodeFactory.create(event=event)
        ec2 = EventCodeFactory.create(event=event)
        other_event = EventFactory.create()

        data = self._run('query { eventList(ordering: "id") { results { id eventCodes { id } } } }')
        by_id = {r["id"]: {e["id"] for e in r["eventCodes"]} for r in data["eventList"]["results"]}
        self.assertEqual(by_id[str(event.id)], {str(ec1.id), str(ec2.id)})
        # An event with no codes resolves to an empty list.
        self.assertEqual(by_id[str(other_event.id)], set())
