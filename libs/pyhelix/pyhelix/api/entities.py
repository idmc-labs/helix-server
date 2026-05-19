from __future__ import annotations

import abc
import logging
import math
import typing

import httpx
import typing_extensions

from .queries import GraphqlQuery

logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from .api import HelixClient


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


class HelixEntityManager:
    fetch_manager: type[HelixEntityManagerFetcher]

    def __init__(self, helix_client: HelixClient):
        self.helix_client = helix_client

        self._fetch_manager = self.fetch_manager(helix_client)

        self._entities = list(self._fetch_manager.fetch())
        self._entities_map = {obj["name"].lower(): obj["id"] for obj in self._entities}
        self._entities_ids_set = {str(obj["id"]) for obj in self._entities}

    def search(self, name: str) -> int | None:
        # TODO: Maybe use rapidfuzz??
        return self._entities_map.get(name.lower().strip(" "))

    def validate_id_exists(self, _id: int | None) -> int | None:
        if _id is None:
            raise ValueError(f"id for {type(self).__name__} is None (Required)")
        if str(_id) not in self._entities_ids_set:
            raise ValueError(f"Invalid id={_id} for {type(self).__name__}")


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


class HelixOrganization(HelixEntityManager):
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


class HelixCountry(HelixEntityManager):
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
        self._iso3_map = {obj["iso3"].upper(): obj["id"] for obj in self._entities if obj.get("iso3")}
        self._iso2_by_id = {obj["id"]: obj["iso2"] for obj in self._entities if obj.get("iso2")}
        # idmc_short_name is the export's preferred display name; helix Country.name
        # is the formal name and often diverges (e.g. "Syrian Arab Republic" vs "Syria").
        for obj in self._entities:
            short = obj.get("idmcShortName")
            if short:
                self._entities_map.setdefault(short.lower().strip(), obj["id"])

    def search_by_iso3(self, iso3: str | None) -> int | None:
        if not iso3:
            return None
        return self._iso3_map.get(iso3.upper().strip())

    def iso2_by_id(self, country_id: int | None) -> str | None:
        if country_id is None:
            return None
        return self._iso2_by_id.get(country_id)


class HelixViolenceSubType(HelixEntityManager):
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


class HelixDisasterSubType(HelixEntityManager):
    class Fetcher(HelixEntityManagerFetcher):
        helix_model_name = "DisasterSubType"

        @typing_extensions.override
        def _fetch_page(self, page, page_size):
            return self.helix_client.grequest(GraphqlQuery.disaster_sub_types)

        @typing_extensions.override
        def _parse_resp(self, resp):
            return resp.json()["data"]["disasterSubTypeList"]

    fetch_manager = Fetcher


class HelixOtherSubType(HelixEntityManager):
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


class HelixFigureTag(HelixEntityManager):
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
