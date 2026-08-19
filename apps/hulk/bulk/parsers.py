from __future__ import annotations

import datetime
import typing
from enum import Enum

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
