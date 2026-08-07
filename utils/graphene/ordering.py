"""Helpers shared by the chokepoints that turn a client `ordering` string into SQL.

`nulls_last_order_queryset` and `OrderingOnlyArgumentPagination.paginate_queryset`
(`utils/graphene/pagination.py`) serve the top-level and enum-ish lists, and
`_ordering_expressions` (`utils/graphene/dataloaders.py`) the paginated nested lists
`OneToManyLoader` resolves with a `Window(order_by=...)`. All of them need the same readings of
a sort key: what ordering a queryset already carries, which direction it leads with, whether it
already sorts on the primary key, and how to turn its string keys into expressions a `Window`
can resolve.
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
