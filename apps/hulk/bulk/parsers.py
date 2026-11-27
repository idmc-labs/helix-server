from __future__ import annotations

import datetime
import typing
from enum import Enum

from django.db import models

from apps.event.models import NameAttributedModels

EnumT = typing.TypeVar("EnumT", bound=Enum)
NameAttributedModelsT = typing.TypeVar("NameAttributedModelsT", bound=NameAttributedModels)


def get_date_for_graphql(date: typing.Union[datetime.date, datetime.datetime, str]):
    if isinstance(date, datetime.datetime):
        return date.date().isoformat()
    if isinstance(date, datetime.date):
        return date.isoformat()
    # NOTE: Raw value will be handled by mutation serializers
    return date


# TODO: Cache this
def get_name_attributed_model(
    _Model: type[NameAttributedModelsT],
    _id: int | None,
) -> NameAttributedModelsT:
    if _id is None:
        raise ValueError(f"{_Model.__name__} id is None, this is required")
    obj = _Model.objects.filter(id=_id).first()
    if not obj:
        raise ValueError(f"Invalid {_Model.__name__} id={_id}")
    return obj


def validate_ids_exist(
    _Model: type[models.Model],
    ids: typing.Optional[typing.Iterable[int]],
    field_name: str,
) -> None:
    """Reject unknown pks, naming the input field and the offending ids.

    The mutation reports these as ``Invalid pk "…"`` only after the row's entry
    and event exist, so they are cheaper to catch here.
    """
    requested = {int(_id) for _id in ids or []}
    if not requested:
        return
    known = set(_Model.objects.filter(id__in=requested).values_list("id", flat=True))
    missing = sorted(requested - known)
    if missing:
        raise ValueError(f"{field_name}: unknown {_Model.__name__} id(s) {missing}")
