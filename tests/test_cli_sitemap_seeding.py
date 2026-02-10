from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webcrawler.cli import main


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:  # noqa: N802
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/robots.txt":
            # Include Sitemap: so --sitemap-from-robots can discover it.
            base = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"
            body = f"User-agent: *\nDisallow:\nSitemap: {base}/sitemap.xml\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/sitemap.xml":
            base = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"
            body = (
                "<?xml version='1.0' encoding='UTF-8'?>"
                "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>"
                f"<url><loc>{base}/hidden</loc></url>"
                "</urlset>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/":
            body = "<html><body><h2 class='secret_flag'>FLAG: ONE</h2></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        if self.path == "/hidden":
            body = "<html><body><h2 class='secret_flag'>FLAG: HIDDEN</h2></body></html>"
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


def _flags_from_stdout(out: str) -> set[str]:
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def test_cli_seeds_from_explicit_sitemap_url(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--sitemap-url",
                f"{base}/sitemap.xml",
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

    flags = _flags_from_stdout(capsys.readouterr().out)
    assert {"ONE", "HIDDEN"} <= flags


def test_cli_max_depth_0_still_fetches_sitemap_seeds(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--sitemap-url",
                f"{base}/sitemap.xml",
                "--max-depth",
                "0",
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

    flags = _flags_from_stdout(capsys.readouterr().out)
    assert {"ONE", "HIDDEN"} <= flags


def test_cli_sitemap_auto_discovers_sitemap_xml(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--sitemap-auto",
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

    flags = _flags_from_stdout(capsys.readouterr().out)
    assert {"ONE", "HIDDEN"} <= flags


def test_cli_sitemap_from_robots_discovers_sitemap_declarations(capsys) -> None:
    server, base = _start_server()
    try:
        code = main(
            [
                "--start-url",
                f"{base}/",
                "--sitemap-from-robots",
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

    flags = _flags_from_stdout(capsys.readouterr().out)
    assert {"ONE", "HIDDEN"} <= flags
