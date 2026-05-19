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
