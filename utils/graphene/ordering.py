"""Per-model bound on the free-form GraphQL `ordering` argument.

A model bounds itself by declaring an `ORDERING_ALLOWLIST` frozenset. The bound lives on the
model because every chokepoint that validates ordering holds a queryset and never learns which
field is being resolved; lists over the same model therefore share one key set, so a nested
`country { figures }` cannot accept sort keys `figureList` rejects.

One validator, `_ordering_token_allowed` (`utils/graphene/pagination.py`), is reached from two
expression builders: `nulls_last_order_queryset` for the `order_by()` every pagination class in
that module ends at, and `_ordering_expressions` (`utils/graphene/dataloaders.py`) for the
`Window(order_by=...)` a paginated nested list is numbered by. Every list-backing model declares
a set — `TestEveryPaginatedListIsGated` fails if one does not — so a token absent from a model's
set is unreachable on EVERY list over that model, which is what lets a to-many denormalisation be
retired rather than merely unused; see `apps/contrib/tests/test_to_many_ordering_fanout.py`.

Keys are post-`to_snake_case` (`utils/graphene/fields.py` normalises every token before it
reaches the validator) and carry no direction prefix — a leading `-` is stripped first. A key
may name a model field or an annotation the filterset adds; an annotation that has not been
applied fails the resolvability check rather than reaching query compilation.

An EMPTY frozenset is a bound, not an omission: it refuses every explicit `ordering` token
while leaving an unordered request untouched. A model with no `ORDERING_ALLOWLIST` at all falls
back to the resolvability check alone, which accepts to-many paths (the parent fans out, so rows
repeat inside a page) and relation hops onto columns the target model's own set excludes — hence
the registry test requiring one of every model a list is built on. The attribute is read off the
model's own `__dict__` so it is never inherited — an abstract base declaring one must not
silently bound every model built on it.

Widening a set is a deliberate act: `apps/contrib/tests/test_ordering_allowlist_registry.py`
pins the whole registry against a snapshot, so any change has to be recorded there too.
"""

import typing

from django.core.exceptions import FieldDoesNotExist
from django.db.models import F


def declared_ordering(qs) -> list:
    """The ordering `qs` already carries, before any client `ordering` is applied.

    A filterset's own `order_by` first (`OrganizationFilter` buckets country-first matches that
    way), else the model's `Meta.ordering`. The two are not interchangeable: an explicit
    `order_by` is a decision about this queryset and LEADS the client's keys, so the bucket a
    caller asked to be grouped by outranks the sort within it, while `Meta.ordering` is only a
    default and yields to a client's sort key entirely.
    """
    return list(qs.query.order_by) or list(qs.model._meta.ordering or [])


def ordered_column_names(ordering: typing.Iterable) -> typing.Set[str]:
    """The column names `ordering` already sorts on, whatever form its keys take.

    A key is a `"-name"` string on the REST side and an `OrderBy` wrapping an `F` on the GraphQL
    side; an expression naming no column (a `Case`, say) contributes nothing. Callers use this to
    avoid appending a tiebreak the sort already carries.
    """
    names = set()
    for key in ordering:
        if isinstance(key, str):
            names.add(strip_direction(key))
            continue
        expression = getattr(key, "expression", key)
        name = getattr(expression, "name", None)
        if name:
            names.add(strip_direction(name))
    return names


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


def normalise_ordering_token(qs, token):
    """Map a token onto the spelling the allowlist and the ORM use.

    `pk` and `<fk>_id` are exact synonyms of `<pk name>` and `<fk>`, so refusing them would
    reject a client for spelling a permitted column the other way. Direction is preserved.
    """
    prefix, bare = ("-", token[1:]) if token.startswith("-") else ("", token)
    if bare == "pk":
        return prefix + qs.model._meta.pk.name
    if bare.endswith("_id"):
        stem = bare[: -len("_id")]
        try:
            field = qs.model._meta.get_field(stem)
        except FieldDoesNotExist:
            return token
        if field.is_relation:
            return prefix + stem
    return token
