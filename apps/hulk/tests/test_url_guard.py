"""
Tests for the fetch-destination guard used by the hulk attachment downloader.

Two layers are covered:
    - ``validate_fetch_url``: scheme, host resolution, and the private-address
      rules (including the v4-in-v6 spellings of the same internal host).
    - ``download_file``: the guard is re-applied to every redirect hop, so a
      public url cannot bounce the worker into the internal network.

Only numeric-literal hosts are used where a real lookup would happen —
``getaddrinfo`` resolves those locally, so nothing here touches the network.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase, override_settings

from apps.hulk.bulk.handler import MAX_DOWNLOAD_REDIRECTS, download_file
from apps.hulk.bulk.url_guard import UnsafeUrlError, validate_fetch_url

# A publicly routable literal: passes the guard without a DNS round trip.
PUBLIC_URL = "https://93.184.216.34/report.pdf"


def _addrinfo(*addresses: str):
    """Fake ``socket.getaddrinfo`` return shaped like the real one."""
    return [(None, None, None, "", (address, 80)) for address in addresses]


class TestValidateFetchUrl(SimpleTestCase):
    def test_rejects_non_http_schemes(self):
        for url in (
            "file:///etc/passwd",
            "ftp://example.com/a.pdf",
            "s3://bucket/key.pdf",
            "gopher://example.com/",
            "/just/a/path.pdf",
        ):
            with self.subTest(url=url):
                with self.assertRaises(UnsafeUrlError) as cm:
                    validate_fetch_url(url)
                self.assertIn("scheme", str(cm.exception))

    def test_rejects_url_without_host(self):
        with self.assertRaises(UnsafeUrlError):
            validate_fetch_url("http:///no-host.pdf")

    def test_rejects_private_and_internal_literals(self):
        # 169.254.169.254 is the cloud instance-metadata endpoint — the address
        # this guard mainly exists to keep unreachable.
        for host in (
            "127.0.0.1",
            "169.254.169.254",
            "10.1.2.3",
            "192.168.0.5",
            "172.16.0.1",
            "0.0.0.0",
            "[::1]",
            "[fd00::1]",
            "[fe80::1]",
            "224.0.0.1",
        ):
            with self.subTest(host=host):
                with self.assertRaises(UnsafeUrlError):
                    validate_fetch_url(f"http://{host}/creds")

    def test_rejects_ipv4_tunnelled_inside_ipv6(self):
        """The v6 carrier looks global; what it reaches is the metadata host."""
        for host in (
            "[::ffff:169.254.169.254]",  # v4-mapped
            "[2002:a9fe:a9fe::]",  # 6to4 wrapping 169.254.169.254
        ):
            with self.subTest(host=host):
                with self.assertRaises(UnsafeUrlError):
                    validate_fetch_url(f"http://{host}/creds")

    def test_allows_public_literals(self):
        validate_fetch_url(PUBLIC_URL)
        validate_fetch_url("http://8.8.8.8:8080/a.pdf")
        validate_fetch_url("http://[2001:4860:4860::8888]/a.pdf")

    def test_allows_public_hostname(self):
        with patch("apps.hulk.bulk.url_guard.socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
            validate_fetch_url("https://files.example.com/a.pdf")

    def test_rejects_hostname_resolving_to_private_address(self):
        with patch("apps.hulk.bulk.url_guard.socket.getaddrinfo", return_value=_addrinfo("169.254.169.254")):
            with self.assertRaises(UnsafeUrlError):
                validate_fetch_url("https://totally-innocent.example.com/a.pdf")

    def test_rejects_when_any_resolved_address_is_private(self):
        """
        A name with both a public and an internal record must be refused: which
        one the connection picks is not ours to decide.
        """
        with patch(
            "apps.hulk.bulk.url_guard.socket.getaddrinfo",
            return_value=_addrinfo("93.184.216.34", "10.0.0.7"),
        ):
            with self.assertRaises(UnsafeUrlError):
                validate_fetch_url("https://split-horizon.example.com/a.pdf")

    def test_rejects_unresolvable_host(self):
        with patch("apps.hulk.bulk.url_guard.socket.getaddrinfo", side_effect=socket.gaierror("nope")):
            with self.assertRaises(UnsafeUrlError) as cm:
                validate_fetch_url("https://does-not-exist.invalid/a.pdf")
        self.assertIn("could not resolve", str(cm.exception))

    @override_settings(AWS_S3_ENDPOINT_URL="http://minio:9000")
    def test_own_storage_endpoint_is_exempt(self):
        """Helix reading its own bucket over HTTP is not the threat here."""
        validate_fetch_url("http://minio:9000/helix-data/media/old/d.pdf")

    @override_settings(AWS_S3_ENDPOINT_URL=None, HULK_FETCH_ALLOWED_HOSTS=["internal-files"])
    def test_configured_hosts_are_exempt(self):
        validate_fetch_url("http://internal-files/staged/a.pdf")
        # A neighbour on the same private network is still refused — the exemption
        # is per host, not per network.
        with patch("apps.hulk.bulk.url_guard.socket.getaddrinfo", return_value=_addrinfo("10.0.0.9")):
            with self.assertRaises(UnsafeUrlError):
                validate_fetch_url("http://other-internal-files/staged/a.pdf")


def _mock_client(route):
    """
    Patch target for ``httpx.Client`` that serves ``route`` instead of the
    network. Redirects are left unfollowed so ``download_file``'s own hop loop
    is what gets exercised.
    """

    # Bound before patching: the patch replaces ``httpx.Client`` globally, so
    # building the stand-in through the module attribute would recurse.
    real_client_cls = httpx.Client

    def _factory(*args, **kwargs):
        return real_client_cls(transport=httpx.MockTransport(route), follow_redirects=False)

    return patch("apps.hulk.bulk.handler.httpx.Client", _factory)


class TestDownloadFileRedirects(SimpleTestCase):
    def test_downloads_and_names_the_file(self):
        def route(request):
            return httpx.Response(
                200,
                content=b"%PDF-1.4 ...",
                headers={"content-disposition": 'attachment; filename="report.pdf"'},
            )

        with _mock_client(route):
            content_file = download_file(PUBLIC_URL)
        self.assertEqual(content_file.name, "report.pdf")
        self.assertEqual(content_file.read(), b"%PDF-1.4 ...")

    def test_refuses_redirect_into_internal_network(self):
        """The classic bypass: a public url answering 302 → metadata endpoint."""
        seen = []

        def route(request):
            seen.append(str(request.url))
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/iam/"})

        with _mock_client(route):
            with self.assertRaises(UnsafeUrlError):
                download_file(PUBLIC_URL)
        # The internal hop was rejected before it was ever requested.
        self.assertEqual(seen, [PUBLIC_URL])

    def test_follows_a_safe_relative_redirect(self):
        def route(request):
            if request.url.path == "/report.pdf":
                return httpx.Response(302, headers={"location": "/actual.pdf"})
            return httpx.Response(200, content=b"ok", headers={"content-type": "application/pdf"})

        with _mock_client(route):
            content_file = download_file(PUBLIC_URL)
        self.assertEqual(content_file.read(), b"ok")

    def test_gives_up_after_too_many_redirects(self):
        def route(request):
            return httpx.Response(302, headers={"location": "/next"})

        with _mock_client(route):
            with self.assertRaises(httpx.TooManyRedirects):
                download_file(PUBLIC_URL)

    def test_stops_before_exceeding_the_redirect_budget(self):
        """One below the cap still succeeds — the cap is a ceiling, not an off-by-one."""
        seen = []

        def route(request):
            seen.append(str(request.url))
            if len(seen) <= MAX_DOWNLOAD_REDIRECTS:
                return httpx.Response(302, headers={"location": f"/hop-{len(seen)}"})
            return httpx.Response(200, content=b"done", headers={"content-type": "application/pdf"})

        with _mock_client(route):
            content_file = download_file(PUBLIC_URL)
        self.assertEqual(content_file.read(), b"done")
        self.assertEqual(len(seen), MAX_DOWNLOAD_REDIRECTS + 1)
