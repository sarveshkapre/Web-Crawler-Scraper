from __future__ import annotations

import logging
import re
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import lxml.html
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .urltools import is_allowed_host, normalize_url, resolve_and_normalize

LOG = logging.getLogger(__name__)


_FLAG_PREFIX_RE = re.compile(r"^\s*FLAG\s*[:=]\s*", re.IGNORECASE)


@dataclass(frozen=True)
class CrawlConfig:
    start_urls: tuple[str, ...]
    allowed_hosts: set[str] | None
    user_agent: str
    timeout_s: float
    max_pages: int
    delay_s: float
    robots_obey: bool
    extract_secret_flags: bool
    max_flags: int
    max_body_bytes: int | None = None
    exception_retries: int = 0
    max_depth: int | None = None
    robots_fail_closed: bool = False
    respect_canonical: bool = False
    include_patterns: tuple[re.Pattern, ...] = ()
    exclude_patterns: tuple[re.Pattern, ...] = ()
    strip_query_params: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CrawlHooks:
    """
    Optional streaming hooks to keep the crawl engine decoupled from I/O concerns.

    `on_event` receives JSON-serializable dicts suitable for JSONL output.
    """

    on_event: Callable[[dict[str, object]], None] | None = None
    on_flag: Callable[[str], None] | None = None
    on_checkpoint: Callable[[CrawlState], None] | None = None


@dataclass
class CrawlState:
    # frontier items are (url, depth) where depth is hop distance from seeds.
    frontier: deque[tuple[str, int]]
    seen: set[str]
    flags: set[str]
    pages_fetched: int = 0


@dataclass(frozen=True)
class CrawlResult:
    seen: set[str]
    flags: set[str]
    pages_fetched: int


class RobotsCache:
    def __init__(self) -> None:
        self._parsers: dict[str, RobotFileParser] = {}
        self._crawl_delay: dict[str, float] = {}

    def can_fetch(
        self,
        *,
        session: requests.Session,
        user_agent: str,
        url: str,
        timeout_s: float,
        fail_closed: bool,
    ) -> bool:
        parts = urlsplit(url)
        key = f"{parts.scheme.lower()}://{parts.netloc.lower()}"
        rp = self._parsers.get(key)
        if rp is None:
            rp, crawl_delay = _fetch_robots(
                session=session,
                base=key,
                user_agent=user_agent,
                timeout_s=timeout_s,
                fail_closed=fail_closed,
            )
            self._parsers[key] = rp
            if crawl_delay is not None:
                self._crawl_delay[key] = crawl_delay
        return rp.can_fetch(user_agent, url)

    def crawl_delay_s(self, url: str) -> float | None:
        parts = urlsplit(url)
        key = f"{parts.scheme.lower()}://{parts.netloc.lower()}"
        return self._crawl_delay.get(key)


def _fetch_robots(
    *,
    session: requests.Session,
    base: str,
    user_agent: str,
    timeout_s: float,
    fail_closed: bool,
) -> tuple[RobotFileParser, float | None]:
    robots_url = f"{base}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)

    crawl_delay: float | None = None
    try:
        resp = session.get(robots_url, timeout=timeout_s)
        if resp.status_code >= 400:
            # Default: fail-open so the crawler stays useful on hosts with broken robots.
            # In hard politeness mode, fail-closed and disallow all.
            rp.parse(["User-agent: *", "Disallow: /"] if fail_closed else [])
            return rp, None
        lines = resp.text.splitlines()
        rp.parse(lines)
        crawl_delay = _parse_crawl_delay(resp.text, user_agent=user_agent)
    except requests.RequestException:
        rp.parse(["User-agent: *", "Disallow: /"] if fail_closed else [])
    return rp, crawl_delay


def _parse_crawl_delay(body: str, *, user_agent: str) -> float | None:
    """
    Best-effort Crawl-delay parsing.
    robots.txt is not strictly standardized; treat as a hint.
    """
    ua = user_agent.lower()
    agents: list[str] = []
    saw_directive = False
    best_delay: float | None = None
    best_spec = 0  # 2 = exact match, 1 = '*', 0 = none

    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            # Multiple User-agent lines can belong to the same group.
            # If we already saw directives in the current group, a new User-agent starts a new
            # group.
            if saw_directive:
                agents = []
                saw_directive = False
            agents.append(v.lower())
            continue

        if not agents:
            continue
        saw_directive = True

        if k != "crawl-delay":
            continue

        spec = 0
        if ua in agents:
            spec = 2
        elif "*" in agents:
            spec = 1
        else:
            continue

        try:
            d = float(v)
        except ValueError:
            continue

        if spec > best_spec or spec == best_spec:
            best_delay = d
            best_spec = spec

    return best_delay


def build_session(*, user_agent: str, max_retries: int, backoff_factor: float) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent})

    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        status=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


class BodyTooLargeError(ValueError):
    pass


def _read_limited_bytes(resp: requests.Response, *, max_bytes: int | None) -> bytes:
    if max_bytes is None or int(max_bytes) <= 0:
        return resp.content

    # Fast path: honor Content-Length when present to avoid downloading large bodies.
    cl = (resp.headers.get("Content-Length") or "").strip()
    try:
        content_length = int(cl)
    except Exception:
        content_length = None
    if content_length is not None and content_length > int(max_bytes):
        raise BodyTooLargeError(
            f"body exceeded max_bytes={max_bytes} (content_length={content_length})"
        )

    buf = bytearray()
    limit = int(max_bytes)
    for chunk in resp.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        buf.extend(chunk)
        if len(buf) > limit:
            raise BodyTooLargeError(f"body exceeded max_bytes={max_bytes}")
    return bytes(buf)


def login_with_hidden_fields(
    *,
    session: requests.Session,
    login_url: str,
    username: str,
    password: str,
    username_field: str = "username",
    password_field: str = "password",
    timeout_s: float,
) -> str:
    """
    Minimal, form-based login helper:
    - GET login page
    - Extract hidden <input> fields
    - POST with hidden fields + provided credentials
    Returns the final URL after login.
    """
    resp = session.get(login_url, timeout=timeout_s)
    resp.raise_for_status()
    doc = lxml.html.fromstring(resp.text)
    hidden_inputs = doc.xpath(r'//form//input[@type="hidden"]')
    form: dict[str, str] = {}
    for x in hidden_inputs:
        name = x.attrib.get("name")
        if not name:
            continue
        form[name] = x.attrib.get("value", "")
    form[username_field] = username
    form[password_field] = password

    post = session.post(login_url, data=form, timeout=timeout_s, allow_redirects=True)
    post.raise_for_status()
    if normalize_url(post.url) == normalize_url(login_url):
        raise RuntimeError("Login did not redirect; check credentials and login URL.")
    return post.url


def crawl(
    config: CrawlConfig,
    *,
    session: requests.Session,
    hooks: CrawlHooks | None = None,
    state: CrawlState | None = None,
    checkpoint_every: int = 0,
) -> CrawlResult:
    robots = RobotsCache()
    st = state or CrawlState(
        frontier=deque(
            (normalize_url(u, strip_query_params=config.strip_query_params), 0)
            for u in config.start_urls
        ),
        seen=set(),
        flags=set(),
        pages_fetched=0,
    )

    # Per-host pacing.
    next_ok_at: dict[str, float] = {}
    exc_attempts: dict[str, int] = {}

    def _url_allowed(url: str) -> tuple[bool, str | None]:
        if config.include_patterns:
            if not any(r.search(url) for r in config.include_patterns):
                return False, "include_mismatch"
        if config.exclude_patterns:
            if any(r.search(url) for r in config.exclude_patterns):
                return False, "exclude_match"
        return True, None

    def _maybe_checkpoint() -> None:
        if (
            hooks
            and hooks.on_checkpoint
            and checkpoint_every > 0
            and st.pages_fetched > 0
            and st.pages_fetched % checkpoint_every == 0
        ):
            hooks.on_checkpoint(st)

    def _sleep_if_needed(url: str) -> None:
        host = urlsplit(url).netloc.lower()
        t = next_ok_at.get(host)
        if t is None:
            return
        now = time.monotonic()
        if now < t:
            time.sleep(t - now)

    def _record_delay(url: str) -> None:
        host = urlsplit(url).netloc.lower()
        delay = config.delay_s
        robots_delay = robots.crawl_delay_s(url)
        if robots_delay is not None:
            delay = max(delay, robots_delay)
        if delay <= 0:
            return
        next_ok_at[host] = time.monotonic() + delay

    def _extract_canonical_url(*, html_soup: BeautifulSoup, base_url: str) -> str | None:
        for link in html_soup.find_all("link"):
            rel = link.get("rel")
            if not rel:
                continue
            tokens = rel if isinstance(rel, list) else [rel]
            rel_tokens = {str(x).strip().lower() for x in tokens if str(x).strip()}
            if "canonical" not in rel_tokens:
                continue
            href = link.get("href")
            canonical = resolve_and_normalize(
                href,
                base_url=base_url,
                strip_query_params=config.strip_query_params,
            )
            if canonical:
                return canonical
        return None

    while st.frontier and st.pages_fetched < config.max_pages and len(st.flags) < config.max_flags:
        item = st.frontier.popleft()
        if isinstance(item, tuple) and len(item) == 2:
            url, depth = item
            depth = int(depth)
        else:
            url, depth = str(item), 0
        url = normalize_url(url, strip_query_params=config.strip_query_params)

        if url in st.seen:
            continue
        if not is_allowed_host(url, config.allowed_hosts):
            continue
        ok, reason = _url_allowed(url)
        if not ok:
            if hooks and hooks.on_event:
                hooks.on_event({"type": "filtered", "url": url, "reason": reason or "filtered"})
            st.seen.add(url)
            continue

        if config.robots_obey:
            if not robots.can_fetch(
                session=session,
                user_agent=config.user_agent,
                url=url,
                timeout_s=config.timeout_s,
                fail_closed=bool(config.robots_fail_closed),
            ):
                LOG.info("robots: disallowed %s", url)
                if hooks and hooks.on_event:
                    hooks.on_event({"type": "robots_disallow", "url": url})
                st.seen.add(url)
                continue

        # Claim before fetching to avoid duplicate work if it re-enters the frontier.
        st.seen.add(url)
        _sleep_if_needed(url)

        try:
            resp = session.get(url, timeout=config.timeout_s, allow_redirects=False, stream=True)
        except requests.RequestException as e:
            attempts = exc_attempts.get(url, 0)
            will_retry = bool(config.exception_retries) and attempts < int(config.exception_retries)
            LOG.warning("fetch failed url=%s err=%s", url, e)
            if hooks and hooks.on_event:
                ev: dict[str, object] = {"type": "fetch_error", "url": url, "error": str(e)}
                if will_retry:
                    ev["will_retry"] = True
                    ev["retry_num"] = attempts + 1
                    ev["retry_max"] = int(config.exception_retries)
                hooks.on_event(ev)
            if will_retry:
                exc_attempts[url] = attempts + 1
                st.seen.discard(url)
                st.frontier.append((url, depth))
            _record_delay(url)
            continue

        try:
            st.pages_fetched += 1
            fetched_url = normalize_url(resp.url, strip_query_params=config.strip_query_params)
            st.seen.add(fetched_url)
            _record_delay(fetched_url)

            status = resp.status_code
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if hooks and hooks.on_event:
                ev: dict[str, object] = {
                    "type": "fetch",
                    "url": url,
                    "fetched_url": fetched_url,
                    "status": status,
                    "depth": depth,
                }
                if ctype:
                    ev["content_type"] = ctype
                if 300 <= status < 400:
                    loc = resp.headers.get("Location")
                    if loc:
                        redir = resolve_and_normalize(
                            loc, base_url=fetched_url, strip_query_params=config.strip_query_params
                        )
                        if redir:
                            ev["redirect_to"] = redir
                hooks.on_event(ev)
            LOG.debug("fetched status=%s url=%s", status, fetched_url)

            if 300 <= status < 400:
                loc = resp.headers.get("Location")
                if loc:
                    nxt = resolve_and_normalize(
                        loc, base_url=fetched_url, strip_query_params=config.strip_query_params
                    )
                    if (
                        nxt
                        and nxt not in st.seen
                        and is_allowed_host(nxt, config.allowed_hosts)
                        and _url_allowed(nxt)[0]
                    ):
                        st.frontier.append((nxt, depth))
                _maybe_checkpoint()
                continue

            if status >= 400:
                _maybe_checkpoint()
                continue

            if "text/html" not in ctype and "application/xhtml+xml" not in ctype:
                _maybe_checkpoint()
                continue

            try:
                raw = _read_limited_bytes(resp, max_bytes=config.max_body_bytes)
            except BodyTooLargeError:
                if hooks and hooks.on_event:
                    cl = (resp.headers.get("Content-Length") or "").strip()
                    try:
                        content_length = int(cl)
                    except Exception:
                        content_length = None
                    ev = {
                        "type": "body_too_large",
                        "url": url,
                        "fetched_url": fetched_url,
                        "depth": depth,
                        "max_body_bytes": int(config.max_body_bytes or 0),
                    }
                    if content_length is not None:
                        ev["content_length"] = content_length
                    if ctype:
                        ev["content_type"] = ctype
                    hooks.on_event(ev)
                _maybe_checkpoint()
                continue

            enc = resp.encoding or "utf-8"
            html = raw.decode(enc, errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            skip_link_expansion = False
            if config.respect_canonical:
                canonical_url = _extract_canonical_url(html_soup=soup, base_url=fetched_url)
                if canonical_url and canonical_url != fetched_url:
                    canonical_allowed, canonical_reason = _url_allowed(canonical_url)
                    if not canonical_allowed or not is_allowed_host(
                        canonical_url, config.allowed_hosts
                    ):
                        if hooks and hooks.on_event:
                            hooks.on_event(
                                {
                                    "type": "canonical_ignored",
                                    "url": url,
                                    "fetched_url": fetched_url,
                                    "canonical_url": canonical_url,
                                    "reason": canonical_reason or "host_mismatch",
                                }
                            )
                    else:
                        if hooks and hooks.on_event:
                            hooks.on_event(
                                {
                                    "type": "canonical_hint",
                                    "url": url,
                                    "fetched_url": fetched_url,
                                    "canonical_url": canonical_url,
                                }
                            )
                        if canonical_url in st.seen:
                            skip_link_expansion = True
                            if hooks and hooks.on_event:
                                hooks.on_event(
                                    {
                                        "type": "canonical_skip_links",
                                        "url": url,
                                        "fetched_url": fetched_url,
                                        "canonical_url": canonical_url,
                                    }
                                )
                        else:
                            st.frontier.appendleft((canonical_url, depth))

            if config.extract_secret_flags and len(st.flags) < config.max_flags:
                for h2 in soup.find_all("h2", {"class": "secret_flag"}):
                    text = h2.get_text(strip=True)
                    if not text:
                        continue
                    text = _FLAG_PREFIX_RE.sub("", text)
                    if text and text not in st.flags:
                        st.flags.add(text)
                        print(text, flush=True)
                        if hooks and hooks.on_flag:
                            hooks.on_flag(text)
                        if len(st.flags) >= config.max_flags:
                            break

            if skip_link_expansion:
                _maybe_checkpoint()
                continue

            for a in soup.find_all("a"):
                href = a.get("href")
                nxt = resolve_and_normalize(
                    href, base_url=fetched_url, strip_query_params=config.strip_query_params
                )
                if not nxt:
                    continue
                nxt_depth = depth + 1
                if config.max_depth is not None and nxt_depth > config.max_depth:
                    if hooks and hooks.on_event:
                        hooks.on_event({"type": "depth_skip", "url": nxt, "from": fetched_url})
                    continue
                if (
                    nxt not in st.seen
                    and is_allowed_host(nxt, config.allowed_hosts)
                    and _url_allowed(nxt)[0]
                ):
                    st.frontier.append((nxt, nxt_depth))

            _maybe_checkpoint()
        finally:
            resp.close()

    return CrawlResult(seen=set(st.seen), flags=set(st.flags), pages_fetched=int(st.pages_fetched))


def iter_extracted_links(
    html: str, *, base_url: str, strip_query_params: set[str] | frozenset[str] | None = None
) -> Iterable[str]:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        nxt = resolve_and_normalize(
            a.get("href"), base_url=base_url, strip_query_params=strip_query_params
        )
        if nxt:
            yield nxt
