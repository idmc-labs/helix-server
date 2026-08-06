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
from urllib.parse import parse_qs, unquote, urlparse

from django.conf import settings

# AWS S3 host patterns. We deliberately exclude MinIO / GarageHQ / CloudFront /
# anything else so the S3-copy fast path only fires for genuine AWS S3.
_AWS_S3_PATH_STYLE_HOST = re.compile(r"^s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$", re.IGNORECASE)
_AWS_S3_VIRTUAL_HOST = re.compile(r"^([^.]+)\.s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com$", re.IGNORECASE)

# Query parameters that mark a URL as presigned, i.e. as carrying its own
# short-lived read grant in the query string (SigV4 first, then the legacy
# SigV2 form). ``s3.copy_object`` has no way to present such a signature — see
# ``S3Source.is_presigned`` and the attachment handler's fallback.
_PRESIGNED_QUERY_KEYS = frozenset(
    {
        "x-amz-signature",
        "x-amz-credential",
        "x-amz-security-token",
        "x-amz-algorithm",
        "signature",
        "awsaccesskeyid",
    }
)


class S3Source(typing.NamedTuple):
    """
    A bucket + object key resolved from a URL, plus what we know about the URL.

    ``key`` is the best-guess object key; ``fallback_keys`` holds the other
    plausible reading(s) of the same URL path. Both exist because percent
    encoding in a URL is ambiguous for keys containing a literal ``%``:

    * a canonically-encoded URL for the key ``report%20final.pdf`` is
      ``.../report%2520final.pdf`` — decoding once is correct,
    * but exporters routinely paste the raw key into the URL instead
      (``.../report%20final.pdf``), where decoding turns ``%20`` into a space
      and yields a key that does not exist.

    Callers that can probe storage (``head_object``) should walk
    ``key_candidates`` and use the first key that actually resolves rather than
    trusting a single decoding. ``s3://`` URIs are the mirror image: by
    convention they carry the literal key, so there the undecoded path is the
    primary candidate and the decoded form is the fallback.

    ``is_presigned`` is True when the URL's query string carries an AWS
    signature. Such a URL grants read access to whoever holds it, but that
    grant cannot be handed to ``copy_object`` — only an HTTP GET of the full
    URL can use it.
    """

    bucket: str
    key: str
    fallback_keys: typing.Tuple[str, ...] = ()
    is_presigned: bool = False

    @property
    def key_candidates(self) -> typing.Tuple[str, ...]:
        """Keys to try, best guess first."""
        return (self.key, *self.fallback_keys)


def _build_source(
    bucket: typing.Optional[str],
    primary_key: str,
    alternate_key: str,
    *,
    is_presigned: bool = False,
) -> typing.Optional[S3Source]:
    """Assemble an :class:`S3Source`, dropping a redundant/empty alternate key."""
    if not bucket or not primary_key:
        return None
    fallbacks = (alternate_key,) if alternate_key and alternate_key != primary_key else ()
    return S3Source(bucket=bucket, key=primary_key, fallback_keys=fallbacks, is_presigned=is_presigned)


def _is_presigned_query(query: str) -> bool:
    if not query:
        return False
    return any(name.lower() in _PRESIGNED_QUERY_KEYS for name in parse_qs(query, keep_blank_values=True))


def parse_aws_s3_url(url: str) -> typing.Optional[S3Source]:
    """
    Return an :class:`S3Source` if ``url`` points at an AWS S3 object, else ``None``.

    Recognised forms (case-insensitive host; signed-URL query strings are not
    part of the key but do set ``is_presigned``):

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
        # ``s3://`` URIs carry the literal key by convention (that is what the
        # AWS CLI prints and accepts), so the undecoded path wins here.
        raw_key = parsed.path.lstrip("/")
        return _build_source(parsed.hostname, raw_key, unquote(raw_key))
    if scheme not in {"http", "https"}:
        return None
    host = (parsed.hostname or "").lower()
    raw_path = parsed.path.lstrip("/")
    if not raw_path:
        return None
    is_presigned = _is_presigned_query(parsed.query)
    if _AWS_S3_PATH_STYLE_HOST.match(host):
        # Bucket names can never contain '%', so splitting the still-encoded
        # path is safe and keeps the raw key intact for the fallback candidate.
        raw_bucket, _, raw_key = raw_path.partition("/")
        return _build_source(unquote(raw_bucket), unquote(raw_key), raw_key, is_presigned=is_presigned)
    m = _AWS_S3_VIRTUAL_HOST.match(host)
    if m:
        return _build_source(m.group(1), unquote(raw_path), raw_path, is_presigned=is_presigned)
    return None


def parse_same_storage_url(url: str) -> typing.Optional[S3Source]:
    """
    Return an :class:`S3Source` if ``url`` points at helix's configured
    S3-compatible storage endpoint (e.g. MinIO in dev), else ``None``.

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
    raw_path = parsed.path.lstrip("/")
    raw_bucket, _, raw_key = raw_path.partition("/")
    return _build_source(
        unquote(raw_bucket),
        unquote(raw_key),
        raw_key,
        is_presigned=_is_presigned_query(parsed.query),
    )
