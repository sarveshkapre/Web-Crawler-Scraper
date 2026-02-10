from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.crawler import CrawlConfig, CrawlHooks, build_session, crawl


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

        if self.path == "/big":
            filler = "A" * 5000
            body = f"<html><body><a href='/page1'>p1</a>{filler}</body></html>"
            b = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        if self.path == "/page1":
            body = "<html><body>small</body></html>"
            b = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        self.send_response(404)
        self.end_headers()


def _start_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://{host}:{port}"


def test_max_body_bytes_skips_parsing_large_html() -> None:
    _Handler.counts = {}
    server, base = _start_server()
    try:
        session = build_session(user_agent="webcrawler-test/1.0", max_retries=0, backoff_factor=0.0)

        events: list[dict[str, object]] = []
        hooks = CrawlHooks(on_event=lambda ev: events.append(ev))
        config = CrawlConfig(
            start_urls=(f"{base}/big",),
            allowed_hosts=None,
            user_agent="webcrawler-test/1.0",
            timeout_s=2.0,
            max_pages=50,
            max_body_bytes=200,
            delay_s=0.0,
            robots_obey=True,
            extract_secret_flags=False,
            max_flags=10,
            include_patterns=(),
            exclude_patterns=(),
        )

        _ = crawl(config, session=session, hooks=hooks)

        assert any(str(ev.get("type")) == "body_too_large" for ev in events)
        # /page1 is only discoverable via parsing /big; it should never be requested.
        assert _Handler.counts.get("/page1", 0) == 0
    finally:
        server.shutdown()

