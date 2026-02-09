from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import deque
from pathlib import Path

from .crawler import (
    CrawlConfig,
    CrawlHooks,
    CrawlState,
    build_session,
    crawl,
    login_with_hidden_fields,
)
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
            # Optionally seed extra start URLs into the frontier for convenience.
            for u in start_urls:
                if u not in crawl_state.seen:
                    crawl_state.frontier.append(u)
            if not start_urls:
                start_urls = list(persisted.start_urls)
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

    allowed_hosts = set(h.lower() for h in args.allowed_domain) if args.allowed_domain else None
    if allowed_hosts is None:
        if start_urls:
            allowed_hosts = {host_for_url(u) for u in start_urls}
        elif persisted is not None:
            allowed_hosts = persisted.allowed_hosts

    if args.state and crawl_state is None:
        # New persisted crawl: initialize state explicitly so it can be checkpointed.
        crawl_state = CrawlState(
            frontier=deque(start_urls),
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
        delay_s=args.delay,
        robots_obey=bool(args.robots),
        extract_secret_flags=bool(args.extract_secret_flags),
        max_flags=args.max_flags,
    )

    def _checkpoint(st: CrawlState) -> None:
        if not args.state:
            return
        save_state(args.state, state=st, start_urls=config.start_urls, allowed_hosts=allowed_hosts)

    hooks = CrawlHooks(on_checkpoint=_checkpoint if args.state else None)
    out_urls = None
    out_flags = None
    try:
        if args.out_urls:
            out_urls = _open_output(args.out_urls, append=bool(args.append_output))

            def _on_event(ev: dict[str, object]) -> None:
                out_urls.write(json.dumps(ev, sort_keys=True) + "\n")

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
    try:
        seen, flags = crawl(
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
        status = 1
    finally:
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
        if out_urls:
            out_urls.close()
        if out_flags:
            out_flags.close()

    if status != 0:
        return status

    logging.getLogger(__name__).info("done pages=%s flags=%s", len(seen), len(flags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
