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
    frontier: deque[str]
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
        self, *, session: requests.Session, user_agent: str, url: str, timeout_s: float
    ) -> bool:
        parts = urlsplit(url)
        key = f"{parts.scheme.lower()}://{parts.netloc.lower()}"
        rp = self._parsers.get(key)
        if rp is None:
            rp, crawl_delay = _fetch_robots(
                session=session, base=key, user_agent=user_agent, timeout_s=timeout_s
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
    *, session: requests.Session, base: str, user_agent: str, timeout_s: float
) -> tuple[RobotFileParser, float | None]:
    robots_url = f"{base}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)

    crawl_delay: float | None = None
    try:
        resp = session.get(robots_url, timeout=timeout_s)
        if resp.status_code >= 400:
            rp.parse([])
            return rp, None
        lines = resp.text.splitlines()
        rp.parse(lines)
        crawl_delay = _parse_crawl_delay(resp.text, user_agent=user_agent)
    except requests.RequestException:
        rp.parse([])  # fail-open: allow crawling if robots can't be fetched
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
        frontier=deque(normalize_url(u) for u in config.start_urls),
        seen=set(),
        flags=set(),
        pages_fetched=0,
    )

    # Per-host pacing.
    next_ok_at: dict[str, float] = {}

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

    while st.frontier and st.pages_fetched < config.max_pages and len(st.flags) < config.max_flags:
        url = st.frontier.popleft()
        url = normalize_url(url)

        if url in st.seen:
            continue
        if not is_allowed_host(url, config.allowed_hosts):
            continue

        if config.robots_obey:
            if not robots.can_fetch(
                session=session, user_agent=config.user_agent, url=url, timeout_s=config.timeout_s
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
            resp = session.get(url, timeout=config.timeout_s, allow_redirects=False)
        except requests.RequestException as e:
            LOG.warning("fetch failed url=%s err=%s", url, e)
            if hooks and hooks.on_event:
                hooks.on_event({"type": "fetch_error", "url": url, "error": str(e)})
            _record_delay(url)
            continue

        st.pages_fetched += 1
        fetched_url = normalize_url(resp.url)
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
            }
            if ctype:
                ev["content_type"] = ctype
            if 300 <= status < 400:
                loc = resp.headers.get("Location")
                if loc:
                    redir = resolve_and_normalize(loc, base_url=fetched_url)
                    if redir:
                        ev["redirect_to"] = redir
            hooks.on_event(ev)
        LOG.debug("fetched status=%s url=%s", status, fetched_url)

        if 300 <= status < 400:
            loc = resp.headers.get("Location")
            if loc:
                nxt = resolve_and_normalize(loc, base_url=fetched_url)
                if nxt and nxt not in st.seen and is_allowed_host(nxt, config.allowed_hosts):
                    st.frontier.append(nxt)
            _maybe_checkpoint()
            continue

        if status >= 400:
            _maybe_checkpoint()
            continue

        if "text/html" not in ctype and "application/xhtml+xml" not in ctype:
            _maybe_checkpoint()
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

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

        for a in soup.find_all("a"):
            href = a.get("href")
            nxt = resolve_and_normalize(href, base_url=fetched_url)
            if not nxt:
                continue
            if nxt not in st.seen and is_allowed_host(nxt, config.allowed_hosts):
                st.frontier.append(nxt)

        _maybe_checkpoint()

    return CrawlResult(seen=set(st.seen), flags=set(st.flags), pages_fetched=int(st.pages_fetched))


def iter_extracted_links(html: str, *, base_url: str) -> Iterable[str]:
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        nxt = resolve_and_normalize(a.get("href"), base_url=base_url)
        if nxt:
            yield nxt
