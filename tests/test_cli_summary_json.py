from __future__ import annotations

import json
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
                "<a href='/private'>private</a>"
                "<h2 class='secret_flag'>FLAG: ONE</h2>"
                "</body></html>"
            )
        elif self.path == "/page1":
            body = "<html><body><h2 class='secret_flag'>FLAG: TWO</h2></body></html>"
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


def _extract_summary(stderr: str) -> dict[str, object]:
    # Logs also go to stderr; find the JSON line we emitted.
    for ln in reversed(stderr.splitlines()):
        ln = ln.strip()
        if ln.startswith("{") and ln.endswith("}"):
            try:
                data = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and "exit_code" in data:
                return data
    raise AssertionError("no summary json found in stderr")


def test_cli_summary_json_defaults_to_stderr(capsys) -> None:
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
                "--summary-json",
            ]
        )
        assert code == 0
    finally:
        server.shutdown()

    cap = capsys.readouterr()
    stdout_flags = {ln.strip() for ln in cap.out.splitlines() if ln.strip()}
    assert {"ONE", "TWO"} <= stdout_flags
    assert "SHOULD_NOT_SEE" not in stdout_flags

    summary = _extract_summary(cap.err)
    assert summary["exit_code"] == 0
    assert summary["flags_found"] >= 2
    assert summary["pages_fetched"] >= 1
    assert summary["terminated_reason"] in {"frontier_empty", "max_pages", "max_flags", "completed"}


def test_cli_summary_json_file_and_append(tmp_path) -> None:
    server, base = _start_server()
    try:
        summary_path = tmp_path / "summary.jsonl"
        code1 = main(
            [
                "--start-url",
                f"{base}/",
                "--max-pages",
                "50",
                "--extract-secret-flags",
                "--max-flags",
                "10",
                "--summary-json",
                str(summary_path),
            ]
        )
        assert code1 == 0
        lines1 = [ln for ln in summary_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines1) == 1
        assert json.loads(lines1[0])["exit_code"] == 0

        code2 = main(
            [
                "--start-url",
                f"{base}/",
                "--max-pages",
                "50",
                "--extract-secret-flags",
                "--max-flags",
                "10",
                "--append-output",
                "--summary-json",
                str(summary_path),
            ]
        )
        assert code2 == 0
        lines2 = [ln for ln in summary_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines2) == 2
    finally:
        server.shutdown()

