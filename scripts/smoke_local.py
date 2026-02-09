from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "robots.txt"), "w", encoding="utf-8") as f:
            f.write("User-agent: *\nDisallow: /private.html\n")

        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(
                textwrap.dedent(
                    """\
                    <html><body>
                      <a href="/page1.html">p1</a>
                      <a href="/private.html">private</a>
                      <h2 class="secret_flag">FLAG: SMOKE_ONE</h2>
                    </body></html>
                    """
                )
            )

        with open(os.path.join(d, "page1.html"), "w", encoding="utf-8") as f:
            f.write("<html><body><h2 class='secret_flag'>FLAG: SMOKE_TWO</h2></body></html>")

        with open(os.path.join(d, "private.html"), "w", encoding="utf-8") as f:
            f.write(
                "<html><body><h2 class='secret_flag'>FLAG: SHOULD_NOT_APPEAR</h2></body></html>"
            )

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, fmt: str, *args: object) -> None:
                return

        httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0), lambda *a, **kw: Handler(*a, directory=d, **kw)
        )
        host, port = httpd.server_address
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()

        start_url = f"http://{host}:{port}/index.html"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "webcrawler",
                "--start-url",
                start_url,
                "--extract-secret-flags",
                "--max-flags",
                "10",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        out_lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        print("exit_code=", proc.returncode)
        print("stdout_flags=", out_lines)

        httpd.shutdown()
        return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

