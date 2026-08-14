"""
Destination checks for the URLs a bulk-import row asks the server to fetch.

``file_url`` is operator-supplied and the fetch runs inside the cluster, so a
url is a request made with the importer's network position: everything the
worker can reach and the operator cannot — the cloud instance-metadata endpoint
(169.254.169.254, which hands out the instance role's credentials), internal
admin ports, databases on the private subnet. The response body lands in an
Attachment any helix user can open, so an unchecked url turns "fetch a file"
into "read an internal endpoint and publish the response".

The rule is deny-by-default on where the url resolves, not on how it is
spelled: only ``http(s)``, and only to globally routable addresses. A hostname
blocklist cannot express that — ``http://169.254.169.254/``,
``http://[::ffff:169.254.169.254]/``, ``http://2852039166/`` (integer form) and
an attacker-controlled DNS name with an A record pointing at the same host are
all the same request. Resolving first and judging the resolved addresses
collapses every spelling into one decision.

Redirects are the same problem one hop later: a url on a public host can answer
302 with an internal ``Location``, so each hop needs its own check. That is why
``download_file`` follows redirects itself instead of letting httpx do it.

Residual gap: DNS rebinding. The name is resolved here and again by httpx on
connect, so a record that flips between the two answers passes. Closing it
requires pinning the connection to the checked address and overriding cert
verification's idea of the hostname, which belongs in a transport rather than a
url check; the attacker also has to already be an admin who can run imports.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import typing
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = frozenset({"http", "https"})

_DEFAULT_PORTS = {"http": 80, "https": 443}

_IpAddress = typing.Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


class UnsafeUrlError(Exception):
    """
    Raised when a url must not be fetched: wrong scheme, unresolvable host, or
    a host that resolves to an address outside the public internet.

    The attachment handler turns this into a per-row ``post-errors`` entry, so
    one poisoned row is rejected on its own and the rest of the import runs.
    """


def _embedded_addresses(ip: _IpAddress) -> typing.Iterator[_IpAddress]:
    """
    Yield ``ip`` plus any IPv4 address tunnelled inside it.

    A v6 address can carry a v4 one in its bits, and the carrier reads as
    perfectly global while the payload is not: ``::ffff:169.254.169.254``
    (v4-mapped), ``2002:a9fe:a9fe::`` (6to4) and Teredo addresses all end up
    speaking to the v4 host they embed. Judging only the outer address would
    wave those straight through, so every embedded address is checked too.
    """
    yield ip
    if not isinstance(ip, ipaddress.IPv6Address):
        return
    if ip.ipv4_mapped:
        yield ip.ipv4_mapped
    if ip.sixtofour:
        yield ip.sixtofour
    if ip.teredo:
        # (server, client) — the client half is the tunnelled endpoint, but the
        # server half is dialled too, so neither may be internal.
        yield from ip.teredo


def _rejection_reason(ip: _IpAddress) -> typing.Optional[str]:
    """Return why ``ip`` is off-limits, or ``None`` when it is fine to fetch."""
    for address in _embedded_addresses(ip):
        # ``is_global`` already covers loopback, link-local (169.254/16 — the
        # metadata endpoint), RFC1918, CGNAT, unique-local v6 and the reserved
        # ranges. Multicast is not part of it, hence the second test.
        if address.is_multicast:
            return f"{ip} is a multicast address"
        if not address.is_global:
            return f"{ip} is not a publicly routable address"
    return None


def _exempt_hosts() -> typing.Set[str]:
    """
    Hosts allowed to resolve internally, lower-cased.

    Helix's own object storage is on this list implicitly: in a compose/dev
    checkout ``AWS_S3_ENDPOINT_URL`` is ``http://minio:9000``, a private
    address by construction, and the importer legitimately reads its own
    bucket over HTTP when the server-side copy is not available. Anything else
    has to be named explicitly via ``HULK_FETCH_ALLOWED_HOSTS``, which exists
    for deployments that stage import files on an internal host.
    """
    hosts = {h.strip().lower() for h in (getattr(settings, "HULK_FETCH_ALLOWED_HOSTS", None) or []) if h.strip()}
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None) or ""
    if endpoint:
        endpoint_host = (urlparse(endpoint).hostname or "").lower()
        if endpoint_host:
            hosts.add(endpoint_host)
    return hosts


def validate_fetch_url(url: str) -> None:
    """
    Raise :class:`UnsafeUrlError` unless ``url`` is an ``http(s)`` url whose
    host resolves exclusively to publicly routable addresses.

    *Every* address the host resolves to must pass, not just the first: a name
    with both a public A record and an internal one would otherwise be a coin
    toss decided by resolver ordering, and the connection picks its own.
    """
    parsed = urlparse(url or "")
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"unsupported url scheme {scheme or '(none)'!r}: only http and https may be fetched")

    try:
        host = parsed.hostname
    except ValueError as e:
        # urlparse defers bracket/IPv6 parsing errors to attribute access.
        raise UnsafeUrlError(f"malformed url host: {e}")
    if not host:
        raise UnsafeUrlError("url has no host")
    host = host.lower()

    if host in _exempt_hosts():
        return

    try:
        port = parsed.port or _DEFAULT_PORTS[scheme]
    except ValueError as e:
        raise UnsafeUrlError(f"malformed url port: {e}")

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        # Refusing the row here rather than letting httpx fail keeps the failure
        # message specific, and an unresolvable host is never fetchable anyway.
        raise UnsafeUrlError(f"could not resolve host {host!r}: {e}")

    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise UnsafeUrlError(f"host {host!r} resolved to no addresses")

    for raw in addresses:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            raise UnsafeUrlError(f"host {host!r} resolved to an unparsable address {raw!r}")
        reason = _rejection_reason(ip)
        if reason is not None:
            raise UnsafeUrlError(f"host {host!r} resolves to a blocked address: {reason}")
