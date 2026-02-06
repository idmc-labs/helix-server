from __future__ import annotations

import json
import typing
from enum import Enum

from pydantic import BeforeValidator

EnumT = typing.TypeVar("EnumT", bound=Enum)


def json_parser():
    def _parse(v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    return BeforeValidator(_parse)


# TODO: Cache this
def get_enum_from_string(enum_cls: type[EnumT], value: str) -> EnumT | None:
    _value = value.upper()

    # Try enum name
    enum_obj = enum_cls.__members__.get(_value)
    if enum_obj is not None:
        return enum_obj

    # Try enum label
    enum_value = {str(_label).upper(): _enum for _enum, _label in getattr(enum_cls, "__labels__", {}).items()}.get(_value)

    if enum_value is None:
        return

    return enum_cls(enum_value)


# TODO: Cache this
@typing.overload
def validate_and_parse_enum(
    enum_cls: typing.Type[EnumT],
    value: str | EnumT,
    is_required: typing.Literal[False],
) -> EnumT | None: ...
@typing.overload
def validate_and_parse_enum(
    enum_cls: typing.Type[EnumT],
    value: str | EnumT,
) -> EnumT | None: ...
@typing.overload
def validate_and_parse_enum(
    enum_cls: typing.Type[EnumT],
    value: str | EnumT,
    is_required: typing.Literal[True],
) -> EnumT: ...
# TODO: Cache this
def validate_and_parse_enum(
    enum_cls: typing.Type[EnumT],
    value: str | EnumT,
    is_required: bool = False,
) -> EnumT | None:
    if isinstance(value, str):
        _value = get_enum_from_string(enum_cls, value)
        if is_required and _value is None:
            raise ValueError(
                f"Invalid event_type '{value}'. Expected one of {[e.value for e in enum_cls]} "
                f"or {[e.name for e in enum_cls]}"
            )
        return _value
    return value


def enum_parser(enum: typing.Type[EnumT], *, required: bool = True):
    def _parse(v):
        return validate_and_parse_enum(enum, v, is_required=required)

    return BeforeValidator(_parse)
