"""Per-model bound on the free-form GraphQL `ordering` argument.

A model bounds itself by declaring an `ORDERING_ALLOWLIST` frozenset. The bound lives on the
model because every chokepoint that validates ordering holds a queryset and never learns which
field is being resolved; lists over the same model therefore share one key set, so a nested
`country { figures }` cannot accept sort keys `figureList` rejects.

All three paths from a client `ordering` string to SQL are gated:
`nulls_last_order_queryset` and `OrderingOnlyArgumentPagination.paginate_queryset`
(`utils/graphene/pagination.py`) for top-level and enum-ish lists, and
`_ordering_expressions` (`utils/graphene/dataloaders.py`) for the paginated nested lists
`FilteredRelationListLoader` resolves with a `Window(order_by=...)`. A token absent from a bounded
model's set is therefore unreachable on EVERY list over that model — which is what lets a
to-many denormalisation be retired rather than merely unused; see
`apps/contrib/tests/test_to_many_ordering_fanout.py`.

Keys are post-`to_snake_case` (`utils/graphene/fields.py` normalises every token before it
reaches the validator) and carry no direction prefix — a leading `-` is stripped first. A key
may name a model field or an annotation the filterset adds; an annotation that has not been
applied fails the resolvability check rather than reaching query compilation.

An EMPTY frozenset is a bound, not an omission: it refuses every explicit `ordering` token
while leaving an unordered request untouched. A model with no `ORDERING_ALLOWLIST` at all is
unbounded and falls back to the resolvability check alone, so such a list degrades rather than
breaks. The attribute is read off the model's own `__dict__` so it is never inherited — an
abstract base declaring one must not silently bound every model built on it.

Widening a set is a deliberate act: `apps/contrib/tests/test_ordering_allowlist_registry.py`
pins the whole registry against a snapshot, so any change has to be recorded there too.
"""

import typing

from django.db.models import F


def declared_ordering(qs) -> list:
    """The ordering `qs` already carries, before any client `ordering` is applied.

    A filterset's own `order_by` first (`OrganizationFilter` buckets country-first matches that
    way), else the model's `Meta.ordering`. The two are not interchangeable: an explicit
    `order_by` is a decision about this queryset and outranks nothing the client asked for,
    while `Meta.ordering` is only a default and must never outrank a client's sort key.
    """
    return list(qs.query.order_by) or list(qs.model._meta.ordering or [])


def leads_descending(ordering: typing.Iterable) -> bool:
    """Whether the first key of `ordering` sorts descending.

    A string carries its own `-` and an `OrderBy` carries `.descending`. A bare expression (a
    `Case`, say) states no direction, so it is skipped rather than read as ascending — the
    direction belongs to the first key that actually has one.
    """
    for key in ordering:
        if isinstance(key, str):
            return key.startswith("-")
        descending = getattr(key, "descending", None)
        if descending is not None:
            return bool(descending)
    return False


def orders_by_pk(ordering: typing.Iterable, pk_name: str) -> bool:
    """Whether `ordering` already sorts on the primary key, so a tiebreaker would be dead.

    An expression is unwrapped one level, since `order_by` accepts both a bare `F("id")` and
    the `OrderBy` that `F("id").asc()` produces.
    """
    for key in ordering:
        if isinstance(key, str):
            name = strip_direction(key)
        else:
            name = getattr(getattr(key, "expression", key), "name", None)
        if name in (pk_name, "pk"):
            return True
    return False


def as_order_expressions(ordering: typing.Iterable) -> list:
    """`ordering` with its string keys turned into expressions.

    A `Window`'s `order_by` resolves a bare string through `F()`, which turns `-created_at`
    into a field named `-created_at`, so a string key has to carry its direction as an
    `OrderBy` instead.
    """
    expressions = []
    for key in ordering:
        if isinstance(key, str):
            expressions.append(F(strip_direction(key)).desc() if key.startswith("-") else F(key).asc())
        else:
            expressions.append(key)
    return expressions


def strip_direction(token: str) -> str:
    """`token` without its direction prefix.

    Exactly one leading `-` comes off, so `--created_at` yields `-created_at` and fails both
    the allowlist and the resolvability check. Stripping every dash would hand `created_at` to
    the validator and then build `F("-created_at")`, whose FieldError enumerates every ORM
    field on the model.
    """
    return token[1:] if token.startswith("-") else token


def get_ordering_allowlist(model) -> typing.Optional[typing.FrozenSet[str]]:
    """The ordering tokens `model`'s lists accept, or None when the model is unbounded.

    Read from the model's own `__dict__` rather than by attribute lookup: every model here
    inherits from an abstract base, and `getattr` would hand a base's set to every child.
    """
    return vars(model).get("ORDERING_ALLOWLIST")
