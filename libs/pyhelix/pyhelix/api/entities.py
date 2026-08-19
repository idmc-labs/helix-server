from __future__ import annotations

import abc
import logging
import math
import typing

import httpx
import typing_extensions
from pydantic import BaseModel, ConfigDict, Field

from .queries import GraphqlQuery

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from .api import HelixClient


class HelixEntityBase(BaseModel):
    """
    Base pydantic model for entities returned by ``HelixEntityManager``.

    GraphQL emits camelCase keys (``idmcShortName``); we accept those via
    ``alias_generator`` while still letting Python code construct entities with
    snake_case kwargs.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda field_name: "".join(
            part if i == 0 else part.title() for i, part in enumerate(field_name.split("_"))
        ),
    )


class HelixOrganizationCountryEntity(HelixEntityBase):
    id: int
    idmc_short_name: str


class HelixOrganizationEntity(HelixEntityBase):
    id: int
    name: str
    countries: typing.List[HelixOrganizationCountryEntity] = Field(default_factory=list)


class HelixCountryEntity(HelixEntityBase):
    id: int
    name: str
    iso2: typing.Optional[str] = None
    iso3: typing.Optional[str] = None
    idmc_short_name: typing.Optional[str] = None


class HelixViolenceSubTypeEntity(HelixEntityBase):
    id: int
    name: str


class HelixDisasterSubTypeEntity(HelixEntityBase):
    id: int
    name: str


class HelixOtherSubTypeEntity(HelixEntityBase):
    id: int
    name: str


class HelixFigureTagEntity(HelixEntityBase):
    id: int
    name: str


EntityT = typing.TypeVar("EntityT", bound=HelixEntityBase)


class HelixEntityManagerFetcher:
    helix_model_name: str

    def __init__(self, helix_client: HelixClient):
        self.helix_client = helix_client

    @abc.abstractmethod
    def _fetch_page(self, page: int, page_size: int) -> httpx.Response:
        raise NotImplementedError()

    @abc.abstractmethod
    def _parse_resp(self, resp: httpx.Response) -> dict:
        raise NotImplementedError()

    def _fetch_all(self):
        page_size = 100

        # Fetch first page
        init_resp = self._fetch_page(1, page_size)
        init_resp_list_data = self._parse_resp(init_resp)

        results = init_resp_list_data.get("results", [])
        total_count = init_resp_list_data.get("totalCount", 0)

        yield from results

        if total_count <= len(results):
            return

        total_pages = math.ceil(total_count / page_size)
        total_fetched = len(results)

        # Fetch remaining pages
        for page in range(2, total_pages + 1):
            resp = self._fetch_page(page, page_size)
            org_list = self._parse_resp(resp)
            results = org_list.get("results", [])
            total_fetched += len(results)
            yield from results

        if total_fetched != total_count:
            logger.warning(
                "Total fetched wasn't same as total_count in remote: (total_count:%s) != (total_fetched:%s)",
                total_count,
                total_fetched,
            )

    def fetch(self):
        logger.info("Fetching data for %s", self.helix_model_name)
        return self._fetch_all()


class HelixEntityManager(typing.Generic[EntityT]):
    fetch_manager: type[HelixEntityManagerFetcher]
    entity_cls: type[EntityT]

    def __init__(self, helix_client: HelixClient):
        self.helix_client = helix_client

        self._fetch_manager = self.fetch_manager(helix_client)

        self._entities: typing.List[EntityT] = [self.entity_cls.model_validate(raw) for raw in self._fetch_manager.fetch()]
        self._entities_by_id: typing.Dict[int, EntityT] = {e.id: e for e in self._entities}
        self._entities_map: typing.Dict[str, EntityT] = {self._search_key(e): e for e in self._entities}

    @staticmethod
    def _normalize(value: str) -> str:
        return value.lower().strip()

    def _search_key(self, entity: EntityT) -> str:
        name = getattr(entity, "name", None)
        if name is None:
            raise AttributeError(f"{type(entity).__name__} has no 'name' attribute for default search")
        return self._normalize(name)

    def search(self, name: str) -> typing.Optional[EntityT]:
        # TODO: Maybe use rapidfuzz??
        return self._entities_map.get(self._normalize(name))

    def validate_id_exists(self, _id: typing.Optional[int]) -> EntityT:
        if _id is None:
            raise ValueError(f"id for {type(self).__name__} is None (Required)")
        entity = self._entities_by_id.get(int(_id))
        if entity is None:
            raise ValueError(f"Invalid id={_id} for {type(self).__name__}")
        return entity


class HelixEntityLazyManagerFetcher:
    """
    Mirrors :class:`HelixEntityManagerFetcher` but for on-demand single-key
    lookups instead of paginated prefetch. ``fetch_one`` is expected to make
    one server call per key and return the matched entity dict (with ``id``)
    or ``None``.
    """

    helix_model_name: str

    def __init__(self, helix_client: HelixClient):
        self.helix_client = helix_client

    @abc.abstractmethod
    def fetch_one(self, key: str) -> typing.Optional[dict]:
        raise NotImplementedError()


class HelixEntityLazyManager:
    """
    Lazy counterpart to :class:`HelixEntityManager`: no prefetch, per-call
    server lookup, process-local cache. Use this when:

      - the entity list is unbounded (e.g. helix users on real deployments)
      - the lookup field is masked by the resolver and can only be matched
        server-side (e.g. ``UserType.email`` is hidden for non-self users)
      - callers only need a handful of values, not the whole list

    Subclasses supply a :class:`HelixEntityLazyManagerFetcher` and inherit
    :meth:`search` for free. ``None``/blank input short-circuits to ``None``;
    repeated lookups for the same key hit the cache.
    """

    fetch_manager: type[HelixEntityLazyManagerFetcher]

    def __init__(self, helix_client: HelixClient):
        self.helix_client = helix_client
        self._fetch_manager = self.fetch_manager(helix_client)
        self._cache: typing.Dict[str, typing.Optional[int]] = {}

    @staticmethod
    def _normalize_key(key: str) -> str:
        return key.strip().lower()

    def search(self, key: str | None) -> int | None:
        if not key:
            return None
        norm = self._normalize_key(key)
        if not norm:
            return None
        if norm in self._cache:
            return self._cache[norm]
        entity = self._fetch_manager.fetch_one(key)
        pk = int(entity["id"]) if entity else None
        self._cache[norm] = pk
        return pk


def _normalize_org_key(value: str) -> str:
    """
    Canonicalize the lookup key for organization labels.

    Matches the format the helix-client renders in the dropdown:
    ``{name} - {idmc_short_name_1, idmc_short_name_2, ...}``. We lowercase,
    expand bare commas to ``", "`` so ``A,B`` and ``A, B`` collapse to the
    same key, and squash any run of whitespace.
    """
    value = value.lower().replace(",", ", ")
    return " ".join(value.split())


class HelixOrganization(HelixEntityManager[HelixOrganizationEntity]):
    """
    Match an organization by its dropdown label (``{name} - {countries}``)
    with a deliberate asymmetric ambiguity policy:

      - **Label** ambiguity (same name AND same country list) → pick the
        highest-id row and warn. These are server-side dupes that are
        interchangeable for the caller's purposes.
      - **Bare-name** ambiguity (same name but different country lists) →
        return ``None`` and warn. The caller's input is underspecified;
        forcing them to pass the full label avoids silently picking a
        cross-country row.
    """

    entity_cls = HelixOrganizationEntity

    class Fetcher(HelixEntityManagerFetcher):
        helix_model_name = "Organization/Source"

        @typing_extensions.override
        def _fetch_page(self, page, page_size):
            return self.helix_client.grequest(
                GraphqlQuery.organizations(
                    page=page,
                    page_size=page_size,
                )
            )

        @typing_extensions.override
        def _parse_resp(self, resp):
            return resp.json()["data"]["organizationList"]

    fetch_manager = Fetcher

    def __init__(self, helix_client: HelixClient):
        super().__init__(helix_client)
        self._label_index: typing.Dict[str, typing.List[HelixOrganizationEntity]] = {}
        self._bare_name_index: typing.Dict[str, typing.List[HelixOrganizationEntity]] = {}
        for entity in self._entities:
            self._label_index.setdefault(self._label_key(entity), []).append(entity)
            self._bare_name_index.setdefault(_normalize_org_key(entity.name), []).append(entity)
        for key, hits in self._label_index.items():
            if len(hits) > 1:
                logger.warning(
                    "duplicate organization label %r ids=%s",
                    key,
                    [h.id for h in hits],
                )

    @staticmethod
    def _label_key(entity: HelixOrganizationEntity) -> str:
        countries = ", ".join(c.idmc_short_name for c in entity.countries)
        label = f"{entity.name} - {countries}" if countries else entity.name
        return _normalize_org_key(label)

    @typing_extensions.override
    def search(self, name: str) -> typing.Optional[HelixOrganizationEntity]:
        key = _normalize_org_key(name)
        hits = self._label_index.get(key)
        if hits:
            if len(hits) == 1:
                return hits[0]
            # Same label = same name AND same countries → server-side dupes.
            # Pick the highest-id row (best-effort recovery).
            chosen = max(hits, key=lambda e: e.id)
            logger.warning(
                "ambiguous label %r — picked latest id=%d from candidates=%s",
                key,
                chosen.id,
                [e.id for e in hits],
            )
            return chosen
        hits = self._bare_name_index.get(key)
        if hits:
            if len(hits) == 1:
                return hits[0]
            distinct_labels = {self._label_key(h) for h in hits}
            if len(distinct_labels) == 1:
                # All candidates share the same label (same countries) — they
                # are interchangeable just like a label-level dupe.
                chosen = max(hits, key=lambda e: e.id)
                logger.warning(
                    "ambiguous bare name %r — all candidates share label; picked latest id=%d from %s",
                    key,
                    chosen.id,
                    [e.id for e in hits],
                )
                return chosen
            logger.warning(
                "ambiguous bare name %r — candidates=%s; pass full label to disambiguate",
                key,
                [e.id for e in hits],
            )
            return None
        return None


class HelixCountry(HelixEntityManager[HelixCountryEntity]):
    entity_cls = HelixCountryEntity

    class Fetcher(HelixEntityManagerFetcher):
        helix_model_name = "Country"

        @typing_extensions.override
        def _fetch_page(self, page, page_size):
            return self.helix_client.grequest(
                GraphqlQuery.countries(
                    page=page,
                    page_size=page_size,
                )
            )

        @typing_extensions.override
        def _parse_resp(self, resp):
            return resp.json()["data"]["countryList"]

    fetch_manager = Fetcher

    def __init__(self, helix_client: HelixClient):
        super().__init__(helix_client)
        self._iso3_map: typing.Dict[str, HelixCountryEntity] = {e.iso3.upper(): e for e in self._entities if e.iso3}
        # idmc_short_name is the export's preferred display name; helix Country.name
        # is the formal name and often diverges (e.g. "Syrian Arab Republic" vs "Syria").
        for entity in self._entities:
            if entity.idmc_short_name:
                self._entities_map.setdefault(self._normalize(entity.idmc_short_name), entity)

    def search_by_iso3(self, iso3: typing.Optional[str]) -> typing.Optional[HelixCountryEntity]:
        if not iso3:
            return None
        return self._iso3_map.get(iso3.upper().strip())


class HelixViolenceSubType(HelixEntityManager[HelixViolenceSubTypeEntity]):
    entity_cls = HelixViolenceSubTypeEntity

    class Fetcher(HelixEntityManagerFetcher):
        helix_model_name = "ViolenceSubType"

        @typing_extensions.override
        def fetch(self):
            resp = self.helix_client.grequest(GraphqlQuery.violence_sub_types)
            yield from [
                sub_type
                for violence in resp.json()["data"]["violenceList"]["results"]
                for sub_type in violence["subTypes"]["results"]
            ]

    fetch_manager = Fetcher


class HelixDisasterSubType(HelixEntityManager[HelixDisasterSubTypeEntity]):
    entity_cls = HelixDisasterSubTypeEntity

    class Fetcher(HelixEntityManagerFetcher):
        helix_model_name = "DisasterSubType"

        @typing_extensions.override
        def _fetch_page(self, page, page_size):
            return self.helix_client.grequest(GraphqlQuery.disaster_sub_types)

        @typing_extensions.override
        def _parse_resp(self, resp):
            return resp.json()["data"]["disasterSubTypeList"]

    fetch_manager = Fetcher


class HelixOtherSubType(HelixEntityManager[HelixOtherSubTypeEntity]):
    entity_cls = HelixOtherSubTypeEntity

    class Fetcher(HelixEntityManagerFetcher):
        helix_model_name = "OtherSubType"

        @typing_extensions.override
        def _fetch_page(self, page, page_size):
            return self.helix_client.grequest(GraphqlQuery.other_sub_types)

        @typing_extensions.override
        def _parse_resp(self, resp):
            return resp.json()["data"]["otherSubTypeList"]

    fetch_manager = Fetcher


class HelixUser(HelixEntityLazyManager):
    """
    Resolve a Helix User PK from an email — used for
    ``HulkBaseModel.impersonate_as``. Lazy because:

      * the user list is unbounded on real deployments, and callers typically
        need only a few emails
      * ``UserType.email`` is masked by the resolver for non-self users, so a
        fetch-all + local email→pk map can't be built; the match has to
        happen server-side via ``UserFilter.email`` (iexact).

    Prefer :meth:`search_by_email` over the inherited :meth:`search` for
    readability — they're the same call.
    """

    class Fetcher(HelixEntityLazyManagerFetcher):
        helix_model_name = "User"

        @typing_extensions.override
        def fetch_one(self, key):
            resp = self.helix_client.grequest(GraphqlQuery.users_by_email(email=key))
            resp.raise_for_status()
            body = resp.json()
            if body.get("errors"):
                raise RuntimeError(f"users graphql errors: {body['errors']}")
            results = body["data"]["users"]["results"] or []
            if not results:
                return None
            if len(results) > 1:
                # iexact + unique email constraint should make this impossible —
                # raise loudly if it ever happens.
                raise RuntimeError(f"users email filter for {key!r} returned {len(results)} matches (expected ≤1)")
            return results[0]

    fetch_manager = Fetcher

    def search_by_email(self, email: str | None) -> int | None:
        return self.search(email)


class HelixFigureTag(HelixEntityManager[HelixFigureTagEntity]):
    entity_cls = HelixFigureTagEntity

    class Fetcher(HelixEntityManagerFetcher):
        helix_model_name = "FigureTag"

        @typing_extensions.override
        def _fetch_page(self, page, page_size):
            return self.helix_client.grequest(
                GraphqlQuery.figure_tags(
                    page=page,
                    page_size=page_size,
                )
            )

        @typing_extensions.override
        def _parse_resp(self, resp):
            return resp.json()["data"]["figureTagList"]

    fetch_manager = Fetcher
