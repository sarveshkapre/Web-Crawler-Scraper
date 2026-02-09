from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.cli import main


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

        if self.path == "/":
            body = (
                "<html><body>"
                "<a href='/page1?utm_source=a'>p1a</a>"
                "<a href='/page1?UTM_MEDIUM=b'>p1b</a>"
                "<h2 class='secret_flag'>FLAG: ONE</h2>"
                "</body></html>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/page1":
            body = "<html><body><h2 class='secret_flag'>FLAG: TWO</h2></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


def _start_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://{host}:{port}"


def test_cli_strip_utm_dedupes_equivalent_urls(capsys) -> None:
    _Handler.counts = {}
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--max-pages",
                "10",
                "--strip-utm",
                "--extract-secret-flags",
                "--max-flags",
                "10",
            ]
        )
        assert code == 0
    finally:
        server.shutdown()

    stdout_flags = {ln.strip() for ln in capsys.readouterr().out.splitlines() if ln.strip()}
    assert {"ONE", "TWO"} <= stdout_flags

    # If utm stripping is applied before dedupe, the crawler should fetch /page1 only once,
    # and should never fetch the query-variant paths.
    assert _Handler.counts.get("/page1", 0) == 1
    assert _Handler.counts.get("/page1?utm_source=a", 0) == 0
    assert _Handler.counts.get("/page1?UTM_MEDIUM=b", 0) == 0

