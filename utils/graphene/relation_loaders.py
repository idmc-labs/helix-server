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
  * ``RelationBatchedDjangoObjectType`` — a base type that, for every exposed forward FK / O2O field
    WITHOUT a hand-written resolver (and not a paginated list), installs a resolver routing through
    ``RelationNodeLoader``. Reverse-FK / M2M list relations are intentionally left for a follow-up
    (they need a grouped list loader; many are already paginated via ``OneToManyLoader``).
"""

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


def _make_fk_resolver(field_name, target_model):
    fk_attr = "%s_id" % field_name

    def resolver(root, info, **kwargs):
        fk_id = getattr(root, fk_attr, None)
        if fk_id is None:
            return None
        return info.context.get_relation_node_loader(target_model).load(fk_id)

    resolver.__name__ = "resolve_%s" % field_name
    return resolver


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
                continue  # paginated list -> OneToManyLoader path
            # concrete forward relation on THIS model: FK (many_to_one) or forward O2O
            if getattr(rel, "concrete", False) and (getattr(rel, "many_to_one", False) or getattr(rel, "one_to_one", False)):
                setattr(cls, "resolve_%s" % snake, _make_fk_resolver(snake, rel.related_model))
