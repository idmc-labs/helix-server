import typing

from django.db import models
from django.db.models import Case, ExpressionWrapper, F, IntegerField, Q, Value, When
from django.db.models.functions import Cast, Mod


class Array(models.Func):
    template = "%(function)s[%(expressions)s]"
    function = "ARRAY"


def rounded_figure_expr(field_name):
    """DB-side `round_and_remove_zero`: integer arithmetic keeps python's
    round-half-even (PG round() breaks ties away from zero) —
    `(n + d/2 - ((n/d + 1) % 2)) / d` floors ties to the even quotient.
    Values here are non-negative sums."""

    def half_even(divisor):
        # PG SUM(bigint) yields NUMERIC, whose division does not truncate —
        # cast back so `/` stays integer division.
        n = Cast(F(field_name), models.BigIntegerField())
        parity = Mod(n / Value(divisor) + Value(1), Value(2))
        return ExpressionWrapper(
            (n + Value(divisor // 2) - parity) / Value(divisor) * Value(divisor),
            output_field=IntegerField(),
        )

    return Case(
        When(
            Q(**{field_name + "__isnull": True}) | Q(**{field_name: 0}),
            then=Value(None, output_field=IntegerField()),
        ),
        When(**{field_name + "__lte": 100}, then=F(field_name)),
        When(**{field_name + "__lte": 1000}, then=half_even(10)),
        When(**{field_name + "__lt": 10000}, then=half_even(100)),
        default=half_even(1000),
        output_field=IntegerField(),
    )


def tiebreak_fields(queryset, ordering: typing.Iterable = ()) -> typing.List[str]:
    """The columns that make a sort over `queryset` total.

    An aggregate has no primary key of its own, and ordering one by `id` folds `id` into the
    GROUP BY -- the compiler adds every non-reference ORDER BY expression to the group -- so the
    page carries one row per underlying figure while `count()`, which clears ordering, keeps
    reporting the grouped total. The group keys are already in the GROUP BY and are unique per
    result row, so they are what makes such a sort total.

    Derived from the queryset rather than named per call site: a grouping that changes takes its
    tiebreak with it, where a hand-written pair silently stops being unique.

    `ordering` names the columns the sort already carries, with or without a `-`; those are skipped
    rather than repeated. The tiebreak is always ascending: making it follow the caller's direction
    needed more machinery than the tidier ORDER BY was worth, and a tie group reading ascending
    under a descending sort is cosmetic where totality is not.
    """
    query = queryset.query
    if query.group_by is None:
        names = [queryset.model._meta.pk.name]
    else:
        names = [
            *query.values_select,
            *(alias for alias, annotation in query.annotation_select.items() if not annotation.contains_aggregate),
        ]
    sorted_on = {key[1:] if key.startswith("-") else key for key in ordering if isinstance(key, str)}
    return [name for name in names if name not in sorted_on]
