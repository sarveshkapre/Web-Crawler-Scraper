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
                "<a href='/page1'>p1</a>"
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
    _Handler.counts = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, f"http://{host}:{port}"


def test_cli_max_depth_0_only_fetches_seeds(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--max-depth",
                "0",
                "--max-pages",
                "50",
                "--extract-secret-flags",
                "--max-flags",
                "10",
            ]
        )
        assert code == 0
    finally:
        server.shutdown()

    flags = {ln.strip() for ln in capsys.readouterr().out.splitlines() if ln.strip()}
    assert flags == {"ONE"}

    assert _Handler.counts.get("/", 0) == 1
    assert _Handler.counts.get("/page1", 0) == 0
    assert _Handler.counts.get("/page2", 0) == 0
