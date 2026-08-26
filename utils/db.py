import typing

from django.db import models


class Array(models.Func):
    template = "%(function)s[%(expressions)s]"
    function = "ARRAY"


def tiebreak_fields(queryset) -> typing.List[str]:
    """The columns that make a sort over `queryset` total.

    An aggregate has no primary key of its own, and ordering one by `id` folds `id` into the
    GROUP BY -- the compiler adds every non-reference ORDER BY expression to the group -- so
    the page carries one row per underlying figure while `count()`, which clears ordering,
    keeps reporting the grouped total. The group keys are already in the GROUP BY and are
    unique per result row, so they are what makes such a sort total.
    """
    query = queryset.query
    if query.group_by is None:
        return [queryset.model._meta.pk.name]
    return [
        *query.values_select,
        *(alias for alias, annotation in query.annotation_select.items() if not annotation.contains_aggregate),
    ]
