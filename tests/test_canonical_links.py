from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.crawler import CrawlConfig, build_session, crawl


class _Handler(BaseHTTPRequestHandler):
    counts: dict[str, int] = {}

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        return

    def _count(self) -> None:
        self.counts[self.path] = self.counts.get(self.path, 0) + 1

    def do_GET(self) -> None:  # noqa: N802
        self._count()

        if self.path == "/robots.txt":
            body = "User-agent: *\nDisallow:\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/real":
            body = "<html><body><a href='/dup1'>dup</a></body></html>"
        elif self.path == "/dup1":
            body = (
                "<html><head><link rel='canonical' href='/real'></head>"
                "<body><a href='/should_skip'>skip</a></body></html>"
            )
        elif self.path == "/should_skip":
            body = "<html><body>skip target</body></html>"
        elif self.path == "/canonical-only":
            body = (
                "<html><head><link rel='canonical' href='/real'></head>"
                "<body>canonical only</body></html>"
            )
        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def _start_server() -> tuple[ThreadingHTTPServer, str]:
    _Handler.counts = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://{host}:{port}"


def test_respect_canonical_skips_duplicate_link_expansion() -> None:
    server, base = _start_server()
    try:
        session = build_session(user_agent="webcrawler-test/1.0", max_retries=0, backoff_factor=0.0)
        config = CrawlConfig(
            start_urls=(f"{base}/real",),
            allowed_hosts=None,
            user_agent="webcrawler-test/1.0",
            timeout_s=2.0,
            max_pages=50,
            delay_s=0.0,
            robots_obey=True,
            respect_canonical=True,
            extract_secret_flags=False,
            max_flags=10,
            include_patterns=(),
            exclude_patterns=(),
        )
        _ = crawl(config, session=session)
    finally:
        server.shutdown()

    assert _Handler.counts.get("/real", 0) == 1
    assert _Handler.counts.get("/dup1", 0) == 1
    assert _Handler.counts.get("/should_skip", 0) == 0


def test_respect_canonical_can_enqueue_unseen_canonical_target() -> None:
    server, base = _start_server()
    try:
        session = build_session(user_agent="webcrawler-test/1.0", max_retries=0, backoff_factor=0.0)
        config = CrawlConfig(
            start_urls=(f"{base}/canonical-only",),
            allowed_hosts=None,
            user_agent="webcrawler-test/1.0",
            timeout_s=2.0,
            max_pages=50,
            delay_s=0.0,
            robots_obey=True,
            respect_canonical=True,
            extract_secret_flags=False,
            max_flags=10,
            include_patterns=(),
            exclude_patterns=(),
        )
        _ = crawl(config, session=session)
    finally:
        server.shutdown()

    assert _Handler.counts.get("/canonical-only", 0) == 1
    assert _Handler.counts.get("/real", 0) == 1
