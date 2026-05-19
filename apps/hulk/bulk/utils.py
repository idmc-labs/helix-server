"""
Utilities for the hulk bulk-import pipeline.

Currently houses the S3-URL parsers used by the attachment handler's
fast path (server-side ``s3.copy_object`` instead of httpx-download).
Kept here so the parsers can be unit-tested in isolation and reused
by future handlers (figures could one day carry attachment-backed
locations, etc.).
"""

from __future__ import annotations

import re
import typing
from urllib.parse import unquote, urlparse

from django.conf import settings

# AWS S3 host patterns. We deliberately exclude MinIO / GarageHQ / CloudFront /
# anything else so the S3-copy fast path only fires for genuine AWS S3.
_AWS_S3_PATH_STYLE_HOST = re.compile(r"^s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$", re.IGNORECASE)
_AWS_S3_VIRTUAL_HOST = re.compile(r"^([^.]+)\.s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$", re.IGNORECASE)


def parse_aws_s3_url(url: str) -> typing.Optional[typing.Tuple[str, str]]:
    """
    Return ``(bucket, key)`` if ``url`` points at an AWS S3 object, else ``None``.

    Recognised forms (case-insensitive host, signed-URL query strings are
    stripped):

    * ``https://<bucket>.s3.<region>.amazonaws.com/<key>``
    * ``https://<bucket>.s3.amazonaws.com/<key>``
    * ``https://<bucket>.s3-<region>.amazonaws.com/<key>``  (legacy)
    * ``https://s3.amazonaws.com/<bucket>/<key>``
    * ``https://s3.<region>.amazonaws.com/<bucket>/<key>``
    * ``s3://<bucket>/<key>``

    Anything else (MinIO, CloudFront, plain HTTP CDN, GarageHQ, etc.) → ``None``.
    """
    if not url:
        return None
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme == "s3":
        bucket = parsed.hostname
        key = unquote(parsed.path.lstrip("/"))
        return (bucket, key) if bucket and key else None
    if scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower()
    key_or_path = unquote(parsed.path.lstrip("/"))
    if not key_or_path:
        return None
    if _AWS_S3_PATH_STYLE_HOST.match(host):
        bucket, _, key = key_or_path.partition("/")
        return (bucket, key) if bucket and key else None
    m = _AWS_S3_VIRTUAL_HOST.match(host)
    if m:
        return m.group(1), key_or_path
    return None


def parse_same_storage_url(url: str) -> typing.Optional[typing.Tuple[str, str]]:
    """
    Return ``(bucket, key)`` if ``url`` points at helix's configured S3-compatible
    storage endpoint (e.g. MinIO in dev), else ``None``.

    The host portion of the URL must match the host of
    ``settings.AWS_S3_ENDPOINT_URL``. The path is parsed path-style as
    ``/<bucket>/<key>``. Once we have bucket+key, ``s3.copy_object`` works
    the same way against MinIO as it does against AWS S3 — the server does
    an internal copy and we never touch the bytes.

    Returns ``None`` when:

    * no ``AWS_S3_ENDPOINT_URL`` is configured (prod / pure-AWS deployment),
    * the URL host doesn't match,
    * the URL is missing a bucket or key.
    """
    endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None) or ""
    if not endpoint or not url:
        return None
    endpoint_host = (urlparse(endpoint).hostname or "").lower()
    if not endpoint_host:
        return None
    parsed = urlparse(url)
    if (parsed.scheme or "").lower() not in {"http", "https"}:
        return None
    if (parsed.hostname or "").lower() != endpoint_host:
        return None
    path = unquote(parsed.path.lstrip("/"))
    bucket, _, key = path.partition("/")
    return (bucket, key) if bucket and key else None
