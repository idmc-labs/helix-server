"""Generic, auto-wired DataLoaders for model relations — the "predictability" layer.

Background: the only thing optimizing relation fields on list endpoints today is
graphene_django_extras' ``queryset_factory`` (via ``DjangoPaginatedListObjectField.get_queryset``).
It select_relates/prefetch_relates a relation ONLY when it is selected exactly ONE level under a
top-level ``*List`` (``recursive_params`` stops at the first relation). That leaves latent N+1s for
the same relation reached at depth>1 (e.g. ``figureList{results{event{violence}}}``) or on
single-object / mutation-result paths where ``queryset_factory`` never runs.

A DataLoader batches per-request across ALL roots at any depth and on any path, so it closes those
gaps. Measured: for a multi-FK type, resolving forward FKs as batched ``in_bulk`` lookups is also
FASTER than a wide multi-table ``select_related`` JOIN (and it dedupes shared targets).

This module provides:
  * ``RelationNodeLoader`` — batch-load a related model's rows by PK (forward FK / OneToOne).
  * ``ReverseFKListLoader`` — batch a reverse-FK list: one query per (parent, accessor), grouped
    by parent id.
  * ``M2MListLoader`` — the same for an M2M, read through the through table.
  * ``ReverseOneToOneLoader`` — batch the reverse side of a OneToOne (one child, or None, per parent).
  * ``RelationBatchedDjangoObjectType`` — a base type that installs a resolver for every exposed
    relation field WITHOUT a hand-written resolver: forward FK / O2O through ``RelationNodeLoader``,
    non-paginated reverse-FK / M2M lists through the grouped list loaders above, and the reverse
    side of a OneToOne through ``ReverseOneToOneLoader``. A field declared as a paginated list is
    left alone — ``FilteredRelationListLoader`` serves those, because they carry the field's own
    filterset, ordering and pagination.

NOTE: the node and list loaders here reach their rows through ``objects``; ``ReverseOneToOneLoader``
uses ``_base_manager``, mirroring ``ReverseOneToOneDescriptor``. Django's own descriptors avoid
``objects`` throughout — ``ForwardManyToOneDescriptor`` resolves an FK through ``_base_manager`` and
``ManyRelatedManager`` derives from the target's ``_default_manager`` — precisely so a filtering
default manager cannot make an existing relation look absent. No model in this project has one, so
they are equivalent today. Give any model a default manager that filters rows and the
``objects``-based loaders will start hiding relations the real descriptor would return.
"""

from collections import defaultdict

from graphene_django import DjangoObjectType
from graphene_django_extras.utils import to_snake_case
from promise import Promise
from promise.dataloader import DataLoader

from utils.graphene.fields import DjangoPaginatedListObjectField


class RelationNodeLoader(DataLoader):
    """Batch-load ``model`` rows by primary key (one loader instance per model per request)."""

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def batch_load_fn(self, keys):
        objs = self.model.objects.in_bulk(keys)
        return Promise.resolve([objs.get(key) for key in keys])


class ReverseFKListLoader(DataLoader):
    """Batch a reverse-FK list: child_model.objects.filter(fk__in=keys), grouped by parent id."""

    def __init__(self, child_model, fk_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.child_model = child_model
        self.fk_name = fk_name

    def batch_load_fn(self, keys):
        fk_id_attr = "%s_id" % self.fk_name
        # Deterministic order: unordered children come back in plan-dependent order, which
        # breaks cross-deployment response comparison. Honour the child's declared ordering
        # first — a bare order_by("pk") silently overrides it (e.g. EventCode.Meta.ordering
        # is ["event_code"], so eventCodes came back in insertion order instead of
        # alphabetical) — then append pk as the tiebreaker Meta.ordering usually lacks.
        ordering = [*(self.child_model._meta.ordering or []), "pk"]
        qs = self.child_model.objects.filter(**{"%s__in" % self.fk_name: keys}).order_by(*ordering)
        grouped = defaultdict(list)
        for obj in qs:
            grouped[getattr(obj, fk_id_attr)].append(obj)
        return Promise.resolve([grouped.get(key, []) for key in keys])


class ReverseOneToOneLoader(DataLoader):
    """Batch a reverse OneToOne: child_model.filter(fk__in=keys), ONE child (or None) per parent."""

    def __init__(self, child_model, fk_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.child_model = child_model
        self.fk_name = fk_name

    def batch_load_fn(self, keys):
        fk_id_attr = "%s_id" % self.fk_name
        # _base_manager mirrors Django's ReverseOneToOneDescriptor.get_queryset, which uses
        # _base_manager so the accessor reports "absent" only when the row really is absent,
        # never because a filtered default manager hid it. This resolver stands in for that
        # descriptor, so `objects` here could turn an existing child into a silent null.
        # No ordering: the FK is UNIQUE, so at most one child exists per key.
        qs = self.child_model._base_manager.filter(**{"%s__in" % self.fk_name: keys})
        by_parent = {getattr(obj, fk_id_attr): obj for obj in qs}
        return Promise.resolve([by_parent.get(key) for key in keys])


class M2MListLoader(DataLoader):
    """Batch an M2M list via the through table: through.filter(source_fk__in=keys), grouped, target select_related."""

    def __init__(self, through, source_fk, target_fk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.through = through
        self.source_fk = source_fk
        self.target_fk = target_fk

    def batch_load_fn(self, keys):
        src_id_attr = "%s_id" % self.source_fk
        # Target-pk order (not through-pk): deterministic and matches what an
        # ordered related manager would return.
        qs = (
            self.through.objects.filter(**{"%s__in" % src_id_attr: keys})
            .select_related(self.target_fk)
            .order_by("%s_id" % self.target_fk)
        )
        grouped = defaultdict(list)
        for row in qs:
            grouped[getattr(row, src_id_attr)].append(getattr(row, self.target_fk))
        return Promise.resolve([grouped.get(key, []) for key in keys])


def _make_fk_resolver(field_name, target_model):
    fk_attr = "%s_id" % field_name

    def resolver(root, info, **kwargs):
        fk_id = getattr(root, fk_attr, None)
        if fk_id is None:
            return None
        return info.context.get_relation_node_loader(target_model).load(fk_id)

    resolver.__name__ = "resolve_%s" % field_name
    return resolver


def _make_list_resolver(field_name, ref, loader_factory):
    def resolver(root, info, **kwargs):
        loader = info.context.get_relation_loader(ref, loader_factory)
        return loader.load(root.id)

    resolver.__name__ = "resolve_%s" % field_name
    return resolver


def _make_reverse_o2o_resolver(field_name, ref, loader_factory):
    # Body-identical to _make_list_resolver but kept separate: the wired resolver's qualname is
    # how the schema-wide structural guard tells the relation kinds apart, and a to-many field
    # silently wired to a single-object loader (or the reverse) would otherwise be invisible.
    def resolver(root, info, **kwargs):
        loader = info.context.get_relation_loader(ref, loader_factory)
        return loader.load(root.id)

    resolver.__name__ = "resolve_%s" % field_name
    return resolver


def _reverse_fk_spec(child_model, fk_name):
    # The ref keys the per-request loader cache, so it must be built from exactly what the
    # loader queries (child model + FK name). Keying by the parent-side accessor collides:
    # two reverse FKs on one parent whose child FKs share a name would share a loader and
    # one field would get the other model's rows.
    ref = "rfk:%s.%s" % (child_model._meta.label, fk_name)
    return ref, lambda: ReverseFKListLoader(child_model, fk_name)


def _reverse_o2o_spec(child_model, fk_name):
    # Same ref discipline as _reverse_fk_spec, with its own prefix: the reverse-O2O loader
    # returns one object where the reverse-FK loader returns a list, so the two must never
    # share a cache entry even for the same (child model, FK).
    ref = "ro2o:%s.%s" % (child_model._meta.label, fk_name)
    return ref, lambda: ReverseOneToOneLoader(child_model, fk_name)


def reverse_fk_list_resolver(child_model, fk_name):
    """Build a class-body resolver for a reverse-FK list field the auto-wire cannot map
    (GraphQL field name differs from the model reverse accessor)."""
    ref, factory = _reverse_fk_spec(child_model, fk_name)
    return _make_list_resolver(ref, ref, factory)


def _list_loader_factory_for(parent_model, rel):
    """Return (ref, factory) for a reverse-FK or M2M relation, or None if unsupported."""
    if rel.one_to_many:  # reverse FK: child has the FK back to parent
        return _reverse_fk_spec(rel.related_model, rel.field.name)
    if rel.many_to_many:
        if hasattr(rel, "m2m_field_name"):  # forward M2M field defined on parent
            through = rel.remote_field.through
            source_fk, target_fk = rel.m2m_field_name(), rel.m2m_reverse_field_name()
        else:  # reverse M2M (ManyToManyRel): the forward field lives on the other model
            f = rel.field
            through = f.remote_field.through
            source_fk, target_fk = f.m2m_reverse_field_name(), f.m2m_field_name()
        # both FK names stay in the ref: forward and reverse traversals of the same through
        # table are different queries and must not share a loader
        ref = "m2m:%s.%s.%s" % (through._meta.label, source_fk, target_fk)
        return (ref, lambda: M2MListLoader(through, source_fk, target_fk))
    return None


class RelationBatchedDjangoObjectType(DjangoObjectType):
    """DjangoObjectType that auto-batches its forward-FK / OneToOne fields via RelationNodeLoader.

    Wiring happens once at class creation: for each exposed field that maps to a concrete
    forward relation (FK / O2O) and has no explicit ``resolve_<field>``, a loader-backed resolver
    is attached. graphene binds resolvers at schema-build time (after all subclasses exist), so
    attributes set here are picked up. Fields with a hand-written resolver, computed fields, and
    paginated lists are left untouched.
    """

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(cls, **options):
        super().__init_subclass_with_meta__(**options)
        model = getattr(cls._meta, "model", None)
        if model is None:
            return
        rels = {f.name: f for f in model._meta.get_fields() if f.is_relation}
        for name in list(cls._meta.fields.keys()):
            snake = to_snake_case(name)
            rel = rels.get(snake) or rels.get(name)
            if rel is None:
                continue
            if getattr(cls, "resolve_%s" % name, None) or getattr(cls, "resolve_%s" % snake, None):
                continue  # explicit resolver / loader already present
            field = cls._meta.fields.get(name)
            if isinstance(field, DjangoPaginatedListObjectField):
                continue  # paginated list -> FilteredRelationListLoader path
            # concrete forward relation on THIS model: FK (many_to_one) or forward O2O -> node loader
            if getattr(rel, "concrete", False) and (getattr(rel, "many_to_one", False) or getattr(rel, "one_to_one", False)):
                setattr(cls, "resolve_%s" % snake, _make_fk_resolver(snake, rel.related_model))
                continue
            # reverse O2O (OneToOneRel): concrete=False and one_to_many=False, so it matches
            # neither branch around it; without this branch it falls through with NO loader
            # at all — one query per parent row.
            if getattr(rel, "one_to_one", False) and not getattr(rel, "concrete", False):
                ref, factory = _reverse_o2o_spec(rel.related_model, rel.field.name)
                setattr(cls, "resolve_%s" % snake, _make_reverse_o2o_resolver(snake, ref, factory))
                continue
            # reverse-FK list / M2M (non-paginated graphene.List) -> grouped list loader
            if getattr(rel, "one_to_many", False) or getattr(rel, "many_to_many", False):
                spec = _list_loader_factory_for(model, rel)
                if spec is not None:
                    ref, factory = spec
                    setattr(cls, "resolve_%s" % snake, _make_list_resolver(snake, ref, factory))
