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
            self.send_response(500)
            self.end_headers()
            return

        if self.path == "/":
            body = "<html><body><h2 class='secret_flag'>FLAG: ONE</h2></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
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


def test_cli_robots_fail_closed_disallows_when_robots_unavailable(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--robots-fail-closed",
                "--max-pages",
                "20",
                "--extract-secret-flags",
                "--max-flags",
                "10",
            ]
        )
        assert code == 0
    finally:
        server.shutdown()

    out = capsys.readouterr().out
    assert "ONE" not in out

    # robots.txt requested, but the start URL should not be fetched.
    assert _Handler.counts.get("/robots.txt", 0) >= 1
    assert _Handler.counts.get("/", 0) == 0
