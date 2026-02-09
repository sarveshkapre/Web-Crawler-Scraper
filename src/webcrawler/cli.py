from __future__ import annotations

import argparse
import logging
import sys

from .crawler import CrawlConfig, build_session, crawl, login_with_hidden_fields
from .urltools import host_for_url, normalize_url


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="webcrawler",
        description="A small, production-minded web crawler and scraper CLI.",
    )

    # Back-compat convenience: `webcrawler USER PASS ...`
    p.add_argument(
        "pos_username",
        nargs="?",
        help="Optional username (positional) for login flows. Prefer --username.",
    )
    p.add_argument(
        "pos_password",
        nargs="?",
        help="Optional password (positional) for login flows. Prefer --password.",
    )

    p.add_argument("--start-url", action="append", default=[], help="Start URL (repeatable).")
    p.add_argument(
        "--allowed-domain",
        action="append",
        default=[],
        help="Allowed host/domain (repeatable). Defaults to host(s) of start URL(s).",
    )
    p.add_argument("--max-pages", type=int, default=500, help="Maximum pages to fetch.")
    p.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds.")
    p.add_argument(
        "--delay", type=float, default=0.0, help="Minimum delay between requests per host."
    )
    p.add_argument(
        "--robots", action=argparse.BooleanOptionalAction, default=True, help="Obey robots.txt."
    )

    p.add_argument("--user-agent", default="webcrawler-scraper/0.1", help="HTTP User-Agent.")
    p.add_argument("--max-retries", type=int, default=2, help="Retry count for transient failures.")
    p.add_argument("--backoff", type=float, default=0.5, help="Retry backoff factor.")

    p.add_argument("--login-url", help="Login URL for form-based auth (optional).")
    p.add_argument("--username", help="Username for login (optional).")
    p.add_argument("--password", help="Password for login (optional).")
    p.add_argument("--username-field", default="username", help="Username field name.")
    p.add_argument("--password-field", default="password", help="Password field name.")

    p.add_argument(
        "--extract-secret-flags",
        action="store_true",
        help="Extract <h2 class='secret_flag'> values and print unique flags to stdout.",
    )
    p.add_argument("--max-flags", type=int, default=5, help="Stop after finding this many flags.")

    p.add_argument("-v", "--verbose", action="count", default=0, help="Increase log verbosity.")
    return p


def _configure_logging(verbosity: int) -> None:
    level = logging.INFO if verbosity <= 0 else logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _configure_logging(args.verbose)

    start_urls = [normalize_url(u) for u in args.start_url]

    user = args.username or args.pos_username
    pwd = args.password or args.pos_password

    session = build_session(
        user_agent=args.user_agent, max_retries=args.max_retries, backoff_factor=args.backoff
    )

    if args.login_url:
        if not user or not pwd:
            print(
                "error: --login-url requires --username/--password (or positional USER PASS).",
                file=sys.stderr,
            )
            return 2
        try:
            final = login_with_hidden_fields(
                session=session,
                login_url=args.login_url,
                username=user,
                password=pwd,
                username_field=args.username_field,
                password_field=args.password_field,
                timeout_s=args.timeout,
            )
        except Exception as e:
            print(f"error: login failed: {e}", file=sys.stderr)
            return 1
        if not start_urls:
            start_urls = [final]

    if not start_urls:
        print(
            "error: at least one --start-url is required (or provide --login-url).",
            file=sys.stderr,
        )
        return 2

    allowed_hosts = set(h.lower() for h in args.allowed_domain) if args.allowed_domain else None
    if allowed_hosts is None:
        allowed_hosts = {host_for_url(u) for u in start_urls}

    config = CrawlConfig(
        start_urls=tuple(start_urls),
        allowed_hosts=allowed_hosts,
        user_agent=args.user_agent,
        timeout_s=args.timeout,
        max_pages=args.max_pages,
        delay_s=args.delay,
        robots_obey=bool(args.robots),
        extract_secret_flags=bool(args.extract_secret_flags),
        max_flags=args.max_flags,
    )

    try:
        seen, flags = crawl(config, session=session)
    except KeyboardInterrupt:
        return 130

    logging.getLogger(__name__).info("done pages=%s flags=%s", len(seen), len(flags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
