from __future__ import annotations

import gzip
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.sitemaps import seed_from_sitemaps


class _Handler(BaseHTTPRequestHandler):
    counts: dict[str, int] = {}

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        return

    def _count(self) -> None:
        self.counts[self.path] = self.counts.get(self.path, 0) + 1

    def do_GET(self) -> None:  # noqa: N802
        self._count()
        base = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"

        if self.path == "/root.xml":
            body = (
                "<?xml version='1.0' encoding='UTF-8'?>"
                "<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
                f"<sitemap><loc>{base}/nested.xml.gz</loc></sitemap>"
                "</sitemapindex>"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/nested.xml.gz":
            xml = (
                "<?xml version='1.0' encoding='UTF-8'?>"
                "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
                f"<url><loc>{base}/a</loc></url>"
                f"<url><loc>{base}/b</loc></url>"
                "</urlset>"
            ).encode()
            body = gzip.compress(xml)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()


def _start_server() -> tuple[ThreadingHTTPServer, str]:
    _Handler.counts = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://{host}:{port}"


def test_seed_from_sitemaps_supports_nested_and_gzip() -> None:
    import requests

    server, base = _start_server()
    try:
        s = requests.Session()
        urls, summary = seed_from_sitemaps(
            session=s,
            sitemap_urls=[f"{base}/root.xml"],
            timeout_s=2.0,
            allowed_hosts=None,
        )
    finally:
        server.shutdown()

    assert f"{base}/a" in urls
    assert f"{base}/b" in urls
    assert summary.sitemaps_fetched == 2
    assert summary.urls_kept == 2


def test_seed_from_sitemaps_obeys_max_sitemaps_limit() -> None:
    import requests

    server, base = _start_server()
    try:
        s = requests.Session()
        urls, summary = seed_from_sitemaps(
            session=s,
            sitemap_urls=[f"{base}/root.xml"],
            timeout_s=2.0,
            allowed_hosts=None,
            max_sitemaps=1,
        )
    finally:
        server.shutdown()

    assert urls == []
    assert summary.sitemaps_fetched == 1
    assert _Handler.counts.get("/nested.xml.gz", 0) == 0
