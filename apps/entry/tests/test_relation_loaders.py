"""Regression coverage for the dataloader-engine + queryset-factory-flip work.

dataloader-engine swapped 16 type modules to ``RelationBatchedDjangoObjectType``, which
auto-wires loader-backed resolvers for relation fields WITHOUT an explicit resolver:
  - forward FK / OneToOne          -> RelationNodeLoader        (_make_fk_resolver)
  - reverse-FK / M2M (plain List)  -> ReverseFKListLoader / M2MListLoader (_make_list_resolver)
queryset-factory-flip then made ``DjangoPaginatedListObjectField.get_queryset`` return a
plain queryset (relations are served by the loaders at ANY depth, not by
graphene_django_extras.queryset_factory which only reached the first level under a list).

These tests assert those changes are BEHAVIOUR-PRESERVING: every relation shape resolves to
the correct value, at depth, with no per-parent (N+1) query fan-out — plus a structural guard
that every auto-wired field across the whole schema still routes through the loader module.
"""

import json

from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    OrganizationFactory,
    ParkingLotFactory,
    TagFactory,
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
    # Reverse-FK list  ->  ReverseFKListLoader
    # ------------------------------------------------------------------ #
    def test_reverse_fk_list_violence_figures(self) -> None:
        violence = ViolenceFactory.create()
        f1 = self._figure(violence=violence)
        f2 = self._figure(violence=violence)
        empty_violence = ViolenceFactory.create()

        data = self._run('query { violenceList(ordering: "id") { results { id figures { id } } } }')
        by_id = {r["id"]: {f["id"] for f in r["figures"]} for r in data["violenceList"]["results"]}
        self.assertEqual(by_id[str(violence.id)], {str(f1.id), str(f2.id)})
        self.assertEqual(by_id[str(empty_violence.id)], set())

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
    def _figure_list_query_count(self, query) -> int:
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
        one = self._figure_list_query_count(query)

        self._figure(created_by=author)
        self._figure(created_by=author)
        many = self._figure_list_query_count(query)

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
        one = self._figure_list_query_count(query)

        f2 = self._figure()
        f2.tags.add(TagFactory.create())
        self._figure()
        many = self._figure_list_query_count(query)

        self.assertEqual(
            one,
            many,
            f"reverse-FK/M2M list resolution scales with row count (N+1): {one} q for 1 figure vs {many} for 3.",
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

        # Baselines enumerated from the engine (37 types / 121 fwd-FK, 27 types / 107 list).
        # >= so legitimate additions don't fail; a drop means a type lost the auto-wiring base.
        self.assertGreaterEqual(fk_count, 121, "auto-wired forward-FK resolvers regressed")
        self.assertGreaterEqual(list_count, 107, "auto-wired reverse-FK/M2M resolvers regressed")

        # Spot-check a few critical fields are loader-wired by name. (NOT `entry`: FigureType.entry
        # keeps the hand-written FigureEntryLoader, so the auto-wire intentionally skips it.)
        from apps.entry.schema import FigureType

        for field in ("event", "country", "created_by", "violence"):
            resolver = getattr(FigureType, "resolve_%s" % field, None)
            self.assertTrue(
                resolver is not None and "relation_loaders" in getattr(resolver, "__module__", ""),
                f"FigureType.{field} is not loader-wired",
            )
