from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.cli import main


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/robots.txt":
            body = "User-agent: *\nDisallow: /private\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
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


def test_cli_exclude_regex_prevents_crawling_matching_urls(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--max-pages",
                "50",
                "--extract-secret-flags",
                "--max-flags",
                "10",
                "--exclude-regex",
                r"/page2$",
            ]
        )
        assert code == 0
    finally:
        server.shutdown()

    stdout_flags = {ln.strip() for ln in capsys.readouterr().out.splitlines() if ln.strip()}
    assert {"ONE", "TWO"} <= stdout_flags
    assert "THREE" not in stdout_flags


def test_cli_include_regex_whitelists_urls(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--max-pages",
                "50",
                "--extract-secret-flags",
                "--max-flags",
                "10",
                # Allow only the start page and /page1.
                "--include-regex",
                r"/$",
                "--include-regex",
                r"/page1$",
            ]
        )
        assert code == 0
    finally:
        server.shutdown()

    stdout_flags = {ln.strip() for ln in capsys.readouterr().out.splitlines() if ln.strip()}
    assert {"ONE", "TWO"} <= stdout_flags
    assert "THREE" not in stdout_flags

