from __future__ import annotations

import contextvars
import enum
import logging
import typing
from contextlib import contextmanager

import httpx

from .entities import (
    HelixCountry,
    HelixDisasterSubType,
    HelixFigureTag,
    HelixOrganization,
    HelixOtherSubType,
    HelixViolenceSubType,
)
from .queries import GraphqlQuery

logger = logging.getLogger(__name__)


class HelixModel(enum.Enum):
    ViolenceSubType = enum.auto()
    DisasterSubType = enum.auto()
    OtherSubType = enum.auto()


class HelixEndpoint:
    class BaseDomain(str, enum.Enum):
        PRODUCTION = "https://helix-tools-api.idmcdb.org"
        STAGING = "https://helix-tools-api-staging.idmcdb.org"

    def __init__(
        self,
        *,
        base_domain: BaseDomain | str,
        email: str,
        password: str,
    ):
        # TODO: Parse base_domain, strip path
        self.base_domain = base_domain.strip("/")
        self.email = email
        self.password = password
        if not (self.base_domain.startswith("https://") or self.base_domain.startswith("http://")):
            raise Exception(f"Invalid base domain: {self.base_domain}")

    @property
    def graphql(self) -> str:
        return f"{self.base_domain}/graphql"


class HelixClient:
    def __init__(self, endpoint: HelixEndpoint):
        self.endpoint = endpoint

        # TODO: Close this properly? Also logout?
        self._client = httpx.Client()

    def grequest(self, _json: dict):
        return self._client.post(
            self.endpoint.graphql,
            json=_json,
        )

    def me(self):
        return self.grequest(GraphqlQuery.me)

    def login(self):
        logger.info("Trying to login into helix server")
        try:
            resp = self.grequest(
                GraphqlQuery.login(
                    self.endpoint.email,
                    self.endpoint.password,
                ),
            )
            resp.raise_for_status()
        except Exception as e:
            raise Exception("Failed to authenticate") from e
        if not resp.json()["data"]["login"]["ok"]:
            raise Exception("Failed to authenticate")
        # TODO: Re-check validation here
        return resp

    @property
    def organization_manager(self) -> HelixOrganization:
        manager = getattr(self, "_organization_manager", None)
        if not manager:
            manager = self._organization_manager = HelixOrganization(self)
        return manager

    @property
    def country_manager(self) -> HelixCountry:
        manager = getattr(self, "_country_manager", None)
        if not manager:
            manager = self._country_manager = HelixCountry(self)
        return manager

    @property
    def violence_sub_type_manager(self) -> HelixViolenceSubType:
        manager = getattr(self, "_violence_sub_type_manager", None)
        if not manager:
            manager = self._violence_sub_type_manager = HelixViolenceSubType(self)
        return manager

    @property
    def disaster_sub_type_manager(self) -> HelixDisasterSubType:
        manager = getattr(self, "_disaster_sub_type_manager", None)
        if not manager:
            manager = self._disaster_sub_type_manager = HelixDisasterSubType(self)
        return manager

    @property
    def other_sub_type_manager(self) -> HelixOtherSubType:
        manager = getattr(self, "_other_sub_type_manager", None)
        if not manager:
            manager = self._other_sub_type_manager = HelixOtherSubType(self)
        return manager

    @property
    def figure_tag_manager(self) -> HelixFigureTag:
        manager = getattr(self, "_figure_tag_manager", None)
        if not manager:
            manager = self._figure_tag_manager = HelixFigureTag(self)
        return manager


# https://docs.python.org/3/library/contextvars.html
current_context: contextvars.ContextVar["HelixClient"] = contextvars.ContextVar("helix_client_current_context")


# TODO: Use HelixClient as context manager?
def get_active_helix_client():
    ctx = typing.cast("HelixClient | None", current_context.get(None))
    if ctx is None:
        raise RuntimeError("HelixClient not set!")
    return ctx


@contextmanager
def helix_client_context(client: HelixClient):
    _client = current_context.set(client)
    try:
        yield
    finally:
        current_context.reset(_client)
