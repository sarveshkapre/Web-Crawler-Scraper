from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit

from .crawler import (
    CrawlConfig,
    CrawlHooks,
    CrawlState,
    build_session,
    crawl,
    login_with_hidden_fields,
)
from .sitemaps import extract_sitemap_urls_from_robots, seed_from_sitemaps
from .state import load_state, save_state
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
    p.add_argument(
        "--max-body-bytes",
        type=int,
        default=0,
        help="Maximum response body bytes to read for HTML parsing/extraction (0 = unlimited).",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum hop depth from seeds (0 = only seed URLs; default: unlimited).",
    )
    p.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds.")
    p.add_argument(
        "--delay", type=float, default=0.0, help="Minimum delay between requests per host."
    )
    p.add_argument(
        "--robots", action=argparse.BooleanOptionalAction, default=True, help="Obey robots.txt."
    )
    p.add_argument(
        "--robots-fail-closed",
        action="store_true",
        help="If robots.txt can't be fetched, disallow crawling that host (default: fail-open).",
    )
    p.add_argument(
        "--respect-canonical",
        action="store_true",
        help=(
            "Respect HTML <link rel='canonical'> hints: if canonical URL was already seen, "
            "skip duplicate page link expansion."
        ),
    )

    p.add_argument("--user-agent", default="webcrawler-scraper/0.1", help="HTTP User-Agent.")
    p.add_argument("--max-retries", type=int, default=2, help="Retry count for transient failures.")
    p.add_argument("--backoff", type=float, default=0.5, help="Retry backoff factor.")
    p.add_argument(
        "--exception-retries",
        type=int,
        default=0,
        help=(
            "If a fetch raises a RequestException (no HTTP response), re-enqueue up to N times "
            "(0 = disabled)."
        ),
    )

    p.add_argument(
        "--include-regex",
        action="append",
        default=[],
        help="Only crawl URLs whose normalized form matches at least one regex (repeatable).",
    )
    p.add_argument(
        "--exclude-regex",
        action="append",
        default=[],
        help="Skip URLs whose normalized form matches any regex (repeatable).",
    )

    p.add_argument(
        "--strip-query-param",
        action="append",
        default=[],
        help="Drop these query parameter names before normalization/dedupe (repeatable).",
    )
    p.add_argument(
        "--strip-utm",
        action="store_true",
        help=(
            "Strip common utm_* tracking params "
            "(utm_source, utm_medium, utm_campaign, utm_term, utm_content, utm_id)."
        ),
    )

    p.add_argument(
        "--sitemap-url",
        action="append",
        default=[],
        help="Seed the crawl frontier from this sitemap URL (repeatable).",
    )
    p.add_argument(
        "--sitemap-auto",
        action="store_true",
        help="Try seeding from /sitemap.xml on the start URL host(s).",
    )
    p.add_argument(
        "--sitemap-from-robots",
        action="store_true",
        help="Discover sitemap URLs via robots.txt Sitemap: declarations on start URL host(s).",
    )
    p.add_argument(
        "--sitemap-max-urls",
        type=int,
        default=20_000,
        help="Maximum number of URLs to seed from sitemaps (0 = no limit).",
    )
    p.add_argument(
        "--sitemap-max-sitemaps",
        type=int,
        default=100,
        help="Maximum number of sitemap documents to fetch when seeding (must be > 0).",
    )
    p.add_argument(
        "--sitemap-max-bytes",
        type=int,
        default=10_000_000,
        help="Maximum bytes to read per sitemap document (must be > 0).",
    )

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

    p.add_argument("--out-urls", help="Write JSONL fetch events to this path (optional).")
    p.add_argument(
        "--out-flags", help="Write extracted flags (one per line) to this path (optional)."
    )
    p.add_argument(
        "--append-output",
        action="store_true",
        help="Append to --out-urls/--out-flags if they exist (default: fail if file exists).",
    )

    p.add_argument("--state", help="Persist crawl state (frontier/visited) to this JSON file.")
    p.add_argument("--resume", action="store_true", help="Resume from an existing --state file.")
    p.add_argument(
        "--checkpoint-every",
        type=int,
        default=50,
        help="Save --state every N fetched pages (0 disables periodic checkpoint).",
    )

    p.add_argument(
        "--summary-json",
        nargs="?",
        const="stderr",
        default=None,
        metavar="PATH",
        help=(
            "Write a one-line JSON summary at the end of the crawl. "
            "If omitted, no summary is written. "
            "If provided without PATH, writes to stderr. "
            "Use PATH to write to a file, or '-' to write to stdout."
        ),
    )

    p.add_argument("-v", "--verbose", action="count", default=0, help="Increase log verbosity.")
    return p


def _configure_logging(verbosity: int) -> None:
    level = logging.INFO if verbosity <= 0 else logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _open_output(path: str, *, append: bool):
    p = Path(path)
    mode = "a" if append else "x"
    # Line-buffer for long crawls so partial outputs survive process termination.
    return p.open(mode, encoding="utf-8", newline="\n", buffering=1)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _configure_logging(args.verbose)

    if int(args.max_pages) <= 0:
        print("error: --max-pages must be > 0.", file=sys.stderr)
        return 2
    if int(args.max_flags) <= 0:
        print("error: --max-flags must be > 0.", file=sys.stderr)
        return 2
    if float(args.timeout) <= 0:
        print("error: --timeout must be > 0.", file=sys.stderr)
        return 2
    if float(args.delay) < 0:
        print("error: --delay must be >= 0.", file=sys.stderr)
        return 2
    if int(args.max_retries) < 0:
        print("error: --max-retries must be >= 0.", file=sys.stderr)
        return 2
    if float(args.backoff) < 0:
        print("error: --backoff must be >= 0.", file=sys.stderr)
        return 2
    if int(args.checkpoint_every) < 0:
        print("error: --checkpoint-every must be >= 0.", file=sys.stderr)
        return 2
    if int(args.sitemap_max_urls) < 0:
        print("error: --sitemap-max-urls must be >= 0.", file=sys.stderr)
        return 2
    if int(args.sitemap_max_sitemaps) <= 0:
        print("error: --sitemap-max-sitemaps must be > 0.", file=sys.stderr)
        return 2
    if int(args.sitemap_max_bytes) <= 0:
        print("error: --sitemap-max-bytes must be > 0.", file=sys.stderr)
        return 2
    if args.max_depth is not None and int(args.max_depth) < 0:
        print("error: --max-depth must be >= 0.", file=sys.stderr)
        return 2
    if args.max_body_bytes is not None and int(args.max_body_bytes) < 0:
        print("error: --max-body-bytes must be >= 0.", file=sys.stderr)
        return 2
    if args.exception_retries is not None and int(args.exception_retries) < 0:
        print("error: --exception-retries must be >= 0.", file=sys.stderr)
        return 2

    strip_query_params: set[str] = {
        str(x).strip().lower() for x in (args.strip_query_param or []) if str(x).strip()
    }
    if args.strip_utm:
        strip_query_params |= {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "utm_id",
        }

    def _norm(u: str) -> str:
        return normalize_url(u, strip_query_params=strip_query_params or None)

    start_urls = [_norm(u) for u in args.start_url]

    include_patterns = []
    for pat in args.include_regex or []:
        try:
            include_patterns.append(re.compile(pat))
        except re.error as e:
            print(f"error: invalid --include-regex pattern {pat!r}: {e}", file=sys.stderr)
            return 2

    exclude_patterns = []
    for pat in args.exclude_regex or []:
        try:
            exclude_patterns.append(re.compile(pat))
        except re.error as e:
            print(f"error: invalid --exclude-regex pattern {pat!r}: {e}", file=sys.stderr)
            return 2

    def _url_allowed(u: str) -> bool:
        if include_patterns and not any(r.search(u) for r in include_patterns):
            return False
        if exclude_patterns and any(r.search(u) for r in exclude_patterns):
            return False
        return True

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

    persisted = None
    crawl_state = None
    if args.state:
        p = Path(args.state)
        if p.exists():
            if not args.resume:
                print("error: --state file exists; use --resume to continue.", file=sys.stderr)
                return 2
            try:
                persisted = load_state(p)
            except Exception as e:
                print(f"error: failed to load state: {e}", file=sys.stderr)
                return 1
            crawl_state = persisted.state
            if strip_query_params:
                # If the caller changes normalization behavior, canonicalize the in-memory state so
                # dedupe/frontier behavior matches the new config.
                canon = deque()
                for item in crawl_state.frontier:
                    if isinstance(item, tuple) and len(item) == 2:
                        u, d = item
                        canon.append((_norm(str(u)), int(d)))
                    else:
                        canon.append((_norm(str(item)), 0))
                crawl_state.frontier = canon
                crawl_state.seen = {_norm(u) for u in crawl_state.seen}
            # Optionally seed extra start URLs into the frontier for convenience.
            for u in start_urls:
                if u not in crawl_state.seen:
                    crawl_state.frontier.append((u, 0))
            if not start_urls:
                start_urls = [_norm(u) for u in persisted.start_urls]
        else:
            if args.resume:
                print("error: --resume requires an existing --state file.", file=sys.stderr)
                return 2

    if not start_urls and not crawl_state:
        print(
            "error: at least one --start-url is required "
            "(or provide --login-url, or use --resume).",
            file=sys.stderr,
        )
        return 2

    if start_urls and any(not _url_allowed(u) for u in start_urls):
        print("error: --start-url is excluded by --include-regex/--exclude-regex.", file=sys.stderr)
        return 2

    allowed_hosts = set(h.lower() for h in args.allowed_domain) if args.allowed_domain else None
    if allowed_hosts is None:
        if start_urls:
            allowed_hosts = {host_for_url(u) for u in start_urls}
        elif persisted is not None:
            allowed_hosts = persisted.allowed_hosts

    if args.state and crawl_state is None:
        # New persisted crawl: initialize state explicitly so it can be checkpointed.
        crawl_state = CrawlState(
            frontier=deque((u, 0) for u in start_urls),
            seen=set(),
            flags=set(),
            pages_fetched=0,
        )

    if crawl_state is None:
        # Use an explicit state even for non-persisted crawls so we can always emit a summary.
        crawl_state = CrawlState(
            frontier=deque((u, 0) for u in start_urls),
            seen=set(),
            flags=set(),
            pages_fetched=0,
        )

    config = CrawlConfig(
        start_urls=tuple(start_urls),
        allowed_hosts=allowed_hosts,
        user_agent=args.user_agent,
        timeout_s=args.timeout,
        max_pages=args.max_pages,
        max_body_bytes=None if int(args.max_body_bytes or 0) <= 0 else int(args.max_body_bytes),
        exception_retries=int(args.exception_retries or 0),
        max_depth=args.max_depth if args.max_depth is None else int(args.max_depth),
        delay_s=args.delay,
        robots_obey=bool(args.robots),
        robots_fail_closed=bool(args.robots_fail_closed),
        respect_canonical=bool(args.respect_canonical),
        extract_secret_flags=bool(args.extract_secret_flags),
        max_flags=args.max_flags,
        include_patterns=tuple(include_patterns),
        exclude_patterns=tuple(exclude_patterns),
        strip_query_params=frozenset(strip_query_params),
    )

    def _checkpoint(st: CrawlState) -> None:
        if not args.state:
            return
        save_state(args.state, state=st, start_urls=config.start_urls, allowed_hosts=allowed_hosts)

    event_counts: dict[str, int] = {}

    def _count_event(ev: dict[str, object]) -> None:
        typ = str(ev.get("type") or "")
        if typ:
            event_counts[typ] = event_counts.get(typ, 0) + 1

    hooks = CrawlHooks(on_checkpoint=_checkpoint if args.state else None)
    out_urls = None
    out_flags = None
    try:
        if args.out_urls:
            out_urls = _open_output(args.out_urls, append=bool(args.append_output))

            def _on_event(ev: dict[str, object]) -> None:
                _count_event(ev)
                out_urls.write(json.dumps(ev, sort_keys=True) + "\n")

            hooks = CrawlHooks(
                on_event=_on_event,
                on_flag=hooks.on_flag,
                on_checkpoint=hooks.on_checkpoint,
            )
        elif args.summary_json:
            # If the caller wants a summary, count events even when not writing JSONL events.
            def _on_event(ev: dict[str, object]) -> None:
                _count_event(ev)

            hooks = CrawlHooks(
                on_event=_on_event,
                on_flag=hooks.on_flag,
                on_checkpoint=hooks.on_checkpoint,
            )

        if args.out_flags:
            out_flags = _open_output(args.out_flags, append=bool(args.append_output))

            def _on_flag(flag: str) -> None:
                out_flags.write(flag + "\n")
                out_flags.flush()

            hooks = CrawlHooks(
                on_event=hooks.on_event,
                on_flag=_on_flag,
                on_checkpoint=hooks.on_checkpoint,
            )
    except FileExistsError as e:
        print(f"error: output file exists (use --append-output): {e.filename}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: could not open output file: {e}", file=sys.stderr)
        return 2

    status = 0
    err_msg: str | None = None
    t0 = time.monotonic()
    try:
        sitemap_urls: list[str] = []
        for u in args.sitemap_url or []:
            sitemap_urls.append(_norm(u))

        # Optional auto-discovery on start URL bases.
        if args.sitemap_auto or args.sitemap_from_robots:
            bases: set[str] = set()
            for u in config.start_urls:
                parts = urlsplit(u)
                if parts.scheme and parts.netloc:
                    bases.add(f"{parts.scheme}://{parts.netloc}")

            if args.sitemap_auto:
                for base in sorted(bases):
                    sitemap_urls.append(_norm(f"{base}/sitemap.xml"))

            if args.sitemap_from_robots:
                for base in sorted(bases):
                    try:
                        resp = session.get(f"{base}/robots.txt", timeout=args.timeout)
                        if resp.status_code < 400:
                            for sm in extract_sitemap_urls_from_robots(resp.text):
                                sitemap_urls.append(_norm(sm))
                    except Exception:
                        continue

        # Deduplicate sitemap URLs, preserving order.
        if sitemap_urls:
            uniq: list[str] = []
            seen: set[str] = set()
            for u in sitemap_urls:
                if u and u not in seen:
                    uniq.append(u)
                    seen.add(u)
            sitemap_urls = uniq

        if sitemap_urls:
            seeded, sm_summary = seed_from_sitemaps(
                session=session,
                sitemap_urls=sitemap_urls,
                timeout_s=float(args.timeout),
                allowed_hosts=allowed_hosts,
                include_patterns=tuple(include_patterns),
                exclude_patterns=tuple(exclude_patterns),
                strip_query_params=strip_query_params or None,
                max_urls=int(args.sitemap_max_urls or 0),
                max_sitemaps=int(args.sitemap_max_sitemaps),
                max_bytes=int(args.sitemap_max_bytes),
            )
            added = 0
            for u in seeded:
                if u not in crawl_state.seen:
                    crawl_state.frontier.append((u, 0))
                    added += 1
            if hooks.on_event:
                hooks.on_event(
                    {
                        "type": "sitemap_seed",
                        "sitemaps_fetched": sm_summary.sitemaps_fetched,
                        "sitemaps_requested": len(sitemap_urls),
                        "urls_added": added,
                        "urls_parsed": sm_summary.urls_parsed,
                        "urls_kept": sm_summary.urls_kept,
                        "errors": sm_summary.errors,
                    }
                )
        _ = crawl(
            config,
            session=session,
            hooks=hooks,
            state=crawl_state,
            checkpoint_every=int(args.checkpoint_every or 0),
        )
    except KeyboardInterrupt:
        status = 130
    except Exception as e:
        print(f"error: crawl failed: {e}", file=sys.stderr)
        err_msg = str(e)
        status = 1
    finally:
        elapsed_s = time.monotonic() - t0
        if args.state and crawl_state is not None:
            try:
                save_state(
                    args.state,
                    state=crawl_state,
                    start_urls=config.start_urls,
                    allowed_hosts=allowed_hosts,
                )
            except Exception as e:
                print(f"error: failed to save state: {e}", file=sys.stderr)
                status = status or 1
                if err_msg is None:
                    err_msg = f"failed to save state: {e}"
        if out_urls:
            out_urls.close()
        if out_flags:
            out_flags.close()

        if args.summary_json:
            if status == 130:
                reason = "interrupt"
            elif status != 0:
                reason = "error"
            elif crawl_state.pages_fetched >= config.max_pages:
                reason = "max_pages"
            elif len(crawl_state.flags) >= config.max_flags:
                reason = "max_flags"
            elif not crawl_state.frontier:
                reason = "frontier_empty"
            else:
                reason = "completed"

            summary: dict[str, object] = {
                "allowed_hosts": sorted(allowed_hosts) if allowed_hosts is not None else None,
                "elapsed_s": round(elapsed_s, 3),
                "error": err_msg,
                "events": dict(sorted(event_counts.items())) if event_counts else {},
                "exit_code": status,
                "flags_found": len(crawl_state.flags),
                "frontier_remaining": len(crawl_state.frontier),
                "max_flags": config.max_flags,
                "max_pages": config.max_pages,
                "pages_fetched": crawl_state.pages_fetched,
                "seen": len(crawl_state.seen),
                "start_urls": list(config.start_urls),
                "terminated_reason": reason,
            }

            line = json.dumps(summary, sort_keys=True) + "\n"
            dest = str(args.summary_json)
            try:
                if dest == "stderr":
                    sys.stderr.write(line)
                    sys.stderr.flush()
                elif dest == "-":
                    sys.stdout.write(line)
                    sys.stdout.flush()
                else:
                    p = Path(dest)
                    mode = "a" if bool(args.append_output) else "x"
                    with p.open(mode, encoding="utf-8", newline="\n") as f:
                        f.write(line)
            except Exception as e:
                print(f"error: failed to write summary json: {e}", file=sys.stderr)
                status = status or 1

    if status != 0:
        return status

    logging.getLogger(__name__).info(
        "done pages=%s flags=%s", crawl_state.pages_fetched, len(crawl_state.flags)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
