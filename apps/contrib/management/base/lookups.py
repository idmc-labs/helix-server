"""
Declarative column resolvers for the bulk-import framework.

Each lookup converts a human-friendly cell value into a serializer-ready value, enumerates its
valid values for the README's "Allowed values" section, and caches its DB reads per run.
"""

import typing

from .utils import DISPLAY_SEP, is_empty


class ResolutionError(Exception):
    """Raised by a lookup when a cell value cannot be resolved to a serializer value."""


def _parse_id(value) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ResolutionError(f"'{value}' is not a valid id")


class BaseLookup:
    """
    Declarative resolver for a single column. Each lookup does three jobs:
    - resolve(): convert a raw cell value into a serializer-ready value (or raise ResolutionError)
    - enumerate_values(): list valid input strings for the README's "Allowed values" grid
    - list_values: whether to list this column's allowed values in the README (False for large tables)
    """

    field: str
    list_values: bool = True
    case_sensitive: bool = True  # name/enum matching is exact; id-based lookups set this False

    def resolve(self, value):
        raise NotImplementedError

    def enumerate_values(self) -> typing.List[str]:
        return []

    def clear_value(self) -> typing.Any:
        """The value that clears this field when the clear-token is used (overridden for list fields)."""
        return None

    def note(self) -> str:
        """A short note for the README, only when the input format is non-obvious (else empty)."""
        return ""

    def duplicate_values(self) -> typing.List[str]:
        """Allowed values that resolve to more than one row (ambiguous); empty for non-DB lookups."""
        return []

    def data_type(self) -> str:
        """The data-type label shown in the README Template Shape table."""
        return "value"

    def reset(self):
        """Drop any cached DB lookups so the next run reads fresh data."""
        self._cache = None


class EnumLookup(BaseLookup):
    """Maps an enum member name (e.g. 'INTERNATIONAL') to its integer value."""

    def __init__(self, field: str, enum_cls, list_values: bool = True):
        self.field = field
        self.enum_cls = enum_cls
        self.list_values = list_values

    def resolve(self, value):
        if is_empty(value):
            # Authoritative blank: hand None to the serializer, which validates whether it is allowed.
            return None
        name = str(value).strip()
        try:
            return self.enum_cls[name].value
        except KeyError:
            raise ResolutionError(f"invalid value '{value}'. Expected one of: {DISPLAY_SEP.join(self.enumerate_values())}")

    def enumerate_values(self) -> typing.List[str]:
        return [member.name for member in self.enum_cls]

    def data_type(self) -> str:
        return "single choice"


class FKByName(BaseLookup):
    """Resolves a foreign key by matching a human-friendly field (e.g. name) against the DB."""

    def __init__(
        self,
        field: str,
        model,
        lookup_field: str = "name",
        error_on_multiple: bool = False,
        list_values: bool = True,
    ):
        self.field = field
        self.model = model
        self.lookup_field = lookup_field
        self.error_on_multiple = error_on_multiple
        self.list_values = list_values
        self._cache: typing.Optional[typing.Dict[str, typing.List[int]]] = None

    @property
    def lookup_map(self) -> typing.Dict[str, typing.List[int]]:
        if self._cache is None:
            cache: typing.Dict[str, typing.List[int]] = {}
            for key, pk in self.model.objects.values_list(self.lookup_field, "pk"):
                cache.setdefault(key, []).append(pk)
            self._cache = cache
        return self._cache

    def resolve(self, value):
        if is_empty(value):
            return None
        key = str(value).strip()
        matches = self.lookup_map.get(key, [])
        if not matches:
            raise ResolutionError(f"no {self.model.__name__} found with {self.lookup_field}='{value}'")
        if len(matches) > 1 and self.error_on_multiple:
            raise ResolutionError(
                f"{len(matches)} {self.model.__name__} rows match {self.lookup_field}='{value}'; cannot disambiguate"
            )
        return matches[0]

    def enumerate_values(self) -> typing.List[str]:
        return sorted(key for key in self.lookup_map.keys() if key is not None)

    # "name" is the default human identifier, so it needs no note; other lookup
    # fields (e.g. iso3) are annotated "by <field>" in the template.
    def note(self) -> str:
        return "" if self.lookup_field == "name" else f"by {self.lookup_field}"

    def duplicate_values(self) -> typing.List[str]:
        return sorted(key for key, pks in self.lookup_map.items() if key is not None and len(pks) > 1)

    def data_type(self) -> str:
        return "single reference"


class M2MByName(BaseLookup):
    """Resolves a many-to-many field from a delimited string of human-friendly keys (e.g. ISO3)."""

    def __init__(
        self,
        field: str,
        model,
        lookup_field: str = "name",
        split: str = ";",
        error_on_multiple: bool = True,
        list_values: bool = True,
    ):
        self.field = field
        self.model = model
        self.lookup_field = lookup_field
        self.split = split
        self.error_on_multiple = error_on_multiple
        self.list_values = list_values
        self._cache: typing.Optional[typing.Dict[str, typing.List[int]]] = None

    @property
    def lookup_map(self) -> typing.Dict[str, typing.List[int]]:
        if self._cache is None:
            cache: typing.Dict[str, typing.List[int]] = {}
            for key, pk in self.model.objects.values_list(self.lookup_field, "pk"):
                if key is not None:
                    cache.setdefault(key, []).append(pk)
            self._cache = cache
        return self._cache

    def resolve(self, value):
        if is_empty(value):
            return []
        keys = [part.strip() for part in str(value).split(self.split) if part.strip()]
        pks, unknown, ambiguous = [], [], []
        for key in keys:
            matches = self.lookup_map.get(key, [])
            if not matches:
                unknown.append(key)
            elif len(matches) > 1 and self.error_on_multiple:
                ambiguous.append(key)
            else:
                pks.append(matches[0])
        if unknown:
            raise ResolutionError(f"no {self.model.__name__} found with {self.lookup_field} in: {DISPLAY_SEP.join(unknown)}")
        if ambiguous:
            raise ResolutionError(
                f"{self.model.__name__} {self.lookup_field} is ambiguous "
                f"(matches multiple rows): {DISPLAY_SEP.join(ambiguous)}"
            )
        return pks

    def clear_value(self):
        return []

    def enumerate_values(self) -> typing.List[str]:
        return sorted(str(key) for key in self.lookup_map.keys())

    # "name" is the default human identifier, so it needs no note; other lookup
    # fields (e.g. iso3) are annotated "by <field>" in the template.
    def note(self) -> str:
        return "" if self.lookup_field == "name" else f"by {self.lookup_field}"

    def duplicate_values(self) -> typing.List[str]:
        return sorted(key for key, pks in self.lookup_map.items() if key is not None and len(pks) > 1)

    def data_type(self) -> str:
        return "multiple reference"


class EnumArrayLookup(BaseLookup):
    """Resolves an ArrayField of enums from a delimited string of enum member names."""

    def __init__(self, field: str, enum_cls, split: str = ";", list_values: bool = True):
        self.field = field
        self.enum_cls = enum_cls
        self.split = split
        self.list_values = list_values

    def resolve(self, value):
        if is_empty(value):
            return []
        names = [part.strip() for part in str(value).split(self.split) if part.strip()]
        values, unknown = [], []
        for name in names:
            try:
                values.append(self.enum_cls[name].value)
            except KeyError:
                unknown.append(name)
        if unknown:
            raise ResolutionError(
                f"invalid value(s) {DISPLAY_SEP.join(unknown)}. Expected one of: {DISPLAY_SEP.join(self.enumerate_values())}"
            )
        return values

    def clear_value(self):
        return []

    def enumerate_values(self) -> typing.List[str]:
        return [member.name for member in self.enum_cls]

    def data_type(self) -> str:
        return "multiple choice"


class QualifiedFKByName(BaseLookup):
    """
    Resolves a foreign key for a hierarchical lookup written as 'Parent > Child'
    (e.g. an org disambiguated by country). Matches the full key string against the DB.
    """

    def __init__(
        self,
        field: str,
        model,
        parent_lookup: str,
        child_lookup: str,
        separator: str = " - ",
        list_values: bool = True,
    ):
        self.field = field
        self.model = model
        self.parent_lookup = parent_lookup
        self.child_lookup = child_lookup
        self.separator = separator
        self.list_values = list_values
        self._cache: typing.Optional[typing.Dict[str, typing.List[int]]] = None

    @property
    def lookup_map(self) -> typing.Dict[str, typing.List[int]]:
        if self._cache is None:
            cache: typing.Dict[str, typing.List[int]] = {}
            for parent, child, pk in self.model.objects.values_list(self.parent_lookup, self.child_lookup, "pk"):
                # With no child (e.g. an org with no country), key on the parent alone, not "<parent> - None".
                key = str(parent) if child is None else f"{parent}{self.separator}{child}"
                cache.setdefault(key, []).append(pk)
            self._cache = cache
        return self._cache

    def resolve(self, value):
        if is_empty(value):
            return None
        key = str(value).strip()
        matches = self.lookup_map.get(key, [])
        if not matches:
            raise ResolutionError(f"no {self.model.__name__} found for '{value}'. Expected 'Parent{self.separator}Child'")
        if len(matches) > 1:
            raise ResolutionError(f"{len(matches)} {self.model.__name__} rows match '{value}'; cannot disambiguate")
        return matches[0]

    def enumerate_values(self) -> typing.List[str]:
        return sorted(self.lookup_map.keys())

    def note(self) -> str:
        return f"format: <parent>{self.separator}<child>"

    def duplicate_values(self) -> typing.List[str]:
        return sorted(key for key, pks in self.lookup_map.items() if key is not None and len(pks) > 1)

    def data_type(self) -> str:
        return "single reference"


class FKById(BaseLookup):
    """
    References a foreign key by primary-key id. Use for high-cardinality models (crisis, event,
    entry, figure) where names are not unique. Not listed in Allowed Choices; not case-sensitive.
    """

    case_sensitive = False

    def __init__(self, field: str, model, list_values: bool = False):
        self.field = field
        self.model = model
        self.list_values = list_values

    def resolve(self, value):
        if is_empty(value):
            return None
        pk = _parse_id(value)
        if not self.model.objects.filter(pk=pk).exists():
            raise ResolutionError(f"no {self.model.__name__} found with id {pk}")
        return pk

    def note(self) -> str:
        return "by id"

    def data_type(self) -> str:
        return "single reference"


class M2MById(BaseLookup):
    """Many-to-many by primary-key ids, delimited (for high-cardinality models). See FKById."""

    case_sensitive = False

    def __init__(self, field: str, model, split: str = ";", list_values: bool = False):
        self.field = field
        self.model = model
        self.split = split
        self.list_values = list_values

    def resolve(self, value):
        if is_empty(value):
            return []
        ids = [_parse_id(part) for part in str(value).split(self.split) if part.strip()]
        found = set(self.model.objects.filter(pk__in=ids).values_list("pk", flat=True))
        missing = [str(pk) for pk in ids if pk not in found]
        if missing:
            raise ResolutionError(f"no {self.model.__name__} found with id(s): {DISPLAY_SEP.join(missing)}")
        return ids

    def note(self) -> str:
        return "by id"

    def data_type(self) -> str:
        return "multiple reference"
