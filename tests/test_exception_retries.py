from __future__ import annotations

import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.crawler import CrawlConfig, CrawlHooks, build_session, crawl


class _Handler(BaseHTTPRequestHandler):
    counts: dict[str, int] = {}

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        return

    def _count(self) -> int:
        n = self.counts.get(self.path, 0) + 1
        self.counts[self.path] = n
        return n

    def do_GET(self) -> None:  # noqa: N802
        n = self._count()

        if self.path == "/robots.txt":
            body = "User-agent: *\nDisallow:\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/flaky":
            # First request: exceed client's timeout so it raises a RequestException.
            if n == 1:
                time.sleep(0.2)
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.connection.close()
                return

            body = "<html><body><a href='/next'>n</a></body></html>"
            b = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        if self.path == "/next":
            body = "<html><body>ok</body></html>"
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


def test_exception_retries_reenqueue_and_eventually_fetch() -> None:
    _Handler.counts = {}
    server, base = _start_server()
    try:
        # Disable requests' internal retries so this test exercises the crawl-level re-enqueue.
        session = build_session(user_agent="webcrawler-test/1.0", max_retries=0, backoff_factor=0.0)

        events: list[dict[str, object]] = []
        hooks = CrawlHooks(on_event=lambda ev: events.append(ev))
        config = CrawlConfig(
            start_urls=(f"{base}/flaky",),
            allowed_hosts=None,
            user_agent="webcrawler-test/1.0",
            timeout_s=0.05,
            max_pages=50,
            delay_s=0.0,
            robots_obey=True,
            extract_secret_flags=False,
            max_flags=10,
            exception_retries=1,
            include_patterns=(),
            exclude_patterns=(),
        )

        _ = crawl(config, session=session, hooks=hooks)

        # First attempt should error, then it should be retried and succeed.
        assert _Handler.counts.get("/flaky", 0) >= 2
        assert any(str(ev.get("type")) == "fetch_error" for ev in events)
        assert any(str(ev.get("type")) == "fetch" and ev.get("status") == 200 for ev in events)
        # /next is only discovered by parsing /flaky, so it should be fetched after a successful
        # retry.
        assert _Handler.counts.get("/next", 0) >= 1
    finally:
        server.shutdown()
