from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.crawler import CrawlConfig, build_session, crawl


class _Handler(BaseHTTPRequestHandler):
    counts: dict[str, int] = {}

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        # Keep tests quiet.
        return

    def _count(self) -> None:
        self.counts[self.path] = self.counts.get(self.path, 0) + 1

    def do_GET(self) -> None:  # noqa: N802
        self._count()

        if self.path == "/robots.txt":
            body = "User-agent: *\nDisallow: /private\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/redir":
            self.send_response(302)
            self.send_header("Location", "/page2")
            self.end_headers()
            return

        if self.path == "/private":
            body = "<html><body><h2 class='secret_flag'>FLAG: SHOULD_NOT_SEE</h2></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/":
            body = (
                "<html><body>"
                "<a href='/page1'>p1</a>"
                "<a href='/private'>private</a>"
                "<a href='/redir'>redir</a>"
                "<h2 class='secret_flag'>FLAG: ONE</h2>"
                "</body></html>"
            )
        elif self.path == "/page1":
            body = (
                "<html><body>"
                "<a href='/page2'>p2</a>"
                "<h2 class='secret_flag'>FLAG: TWO</h2>"
                "</body></html>"
            )
        elif self.path == "/page2":
            body = "<html><body><h2 class='secret_flag'>FLAG: THREE</h2></body></html>"
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
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://{host}:{port}"


def test_crawl_obeys_robots_and_handles_redirects() -> None:
    _Handler.counts = {}
    server, base = _start_server()
    try:
        session = build_session(user_agent="webcrawler-test/1.0", max_retries=0, backoff_factor=0.0)
        config = CrawlConfig(
            start_urls=(f"{base}/",),
            allowed_hosts=None,
            user_agent="webcrawler-test/1.0",
            timeout_s=2.0,
            max_pages=50,
            delay_s=0.0,
            robots_obey=True,
            extract_secret_flags=True,
            max_flags=10,
        )
        result = crawl(config, session=session)

        assert {"ONE", "TWO", "THREE"} <= result.flags
        assert "SHOULD_NOT_SEE" not in result.flags

        # Redirect requested and target fetched eventually.
        assert _Handler.counts.get("/redir", 0) == 1
        assert _Handler.counts.get("/page2", 0) >= 1

        # Disallowed page should not be fetched.
        assert _Handler.counts.get("/private", 0) == 0

        # robots.txt must be fetched at least once.
        assert _Handler.counts.get("/robots.txt", 0) >= 1

        assert any(u.endswith("/") for u in result.seen)
    finally:
        server.shutdown()
