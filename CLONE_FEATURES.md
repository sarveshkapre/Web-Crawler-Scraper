# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do

- [ ] **P2: Concurrency + polite throttling** (Impact 4, Effort 4, Fit 4, Diff 2, Risk 3, Conf 3)
  - Optional parallel fetch with per-host caps + backpressure; keep robots/pacing correct.
- [ ] **P2: Max depth / hop limit** (Impact 3, Effort 3, Fit 4, Diff 2, Risk 2, Conf 3)
  - Add `--max-depth` to bound traversal by link distance from seeds (sitemap seeds count as depth 0).
- [ ] **P3: HTTP cache / conditional GET** (Impact 3, Effort 4, Fit 3, Diff 2, Risk 3, Conf 2)
  - Support `ETag`/`If-Modified-Since` to reduce refetching on repeated crawls.
- [ ] **P3: Extraction rules engine** (Impact 3, Effort 4, Fit 3, Diff 4, Risk 3, Conf 2)
  - CSS selectors via config file; emit extracted fields to JSONL.
- [ ] **P3: Optional JS rendering mode** (Impact 3, Effort 5, Fit 2, Diff 4, Risk 4, Conf 2)
  - Optional Playwright-powered fetcher for JS-heavy pages (explicit opt-in).
- [ ] **P3: Duplicate-content suppression** (Impact 2, Effort 3, Fit 3, Diff 2, Risk 2, Conf 2)
  - Optional body hashing (for HTML only) to avoid revisiting duplicate pages under multiple URLs.
- [ ] **P3: Hard politeness mode** (Impact 2, Effort 2, Fit 3, Diff 2, Risk 2, Conf 2)
  - Add `--robots-fail-closed` to stop on robots fetch/parse failures (default remains fail-open).

## Implemented
- [x] 2026-02-09: Sitemap seeding (`--sitemap-url`, `--sitemap-auto`, `--sitemap-from-robots`) to find non-linked pages. Evidence: `src/webcrawler/sitemaps.py`, `src/webcrawler/cli.py`, `tests/test_cli_sitemap_seeding.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `7e96dc2`.
- [x] 2026-02-09: Optional tracking-param stripping (`--strip-query-param`, `--strip-utm`) applied before normalization/dedupe. Evidence: `src/webcrawler/urltools.py`, `src/webcrawler/crawler.py`, `src/webcrawler/cli.py`, `tests/test_cli_strip_query_params.py`, `tests/test_urltools.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `603971c`.
- [x] 2026-02-09: Structured outputs for automation (`--out-urls` JSONL events, `--out-flags`, `--append-output`). Evidence: `src/webcrawler/cli.py`, `src/webcrawler/crawler.py`, `tests/test_cli_outputs.py`, `README.md`, `make lint`, `make test`. Commit: `eef8325`.
- [x] 2026-02-09: Persistence/resume for long crawls (`--state`, `--resume`, periodic checkpointing). Evidence: `src/webcrawler/state.py`, `src/webcrawler/cli.py`, `src/webcrawler/crawler.py`, `tests/test_cli_resume.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `2c76e2f`.
- [x] 2026-02-09: Improved robots Crawl-delay parsing (multi-User-agent groups; exact UA beats `*`). Evidence: `src/webcrawler/crawler.py`, `tests/test_robots_delay.py`, `make test`. Commit: `2c76e2f`.
- [x] 2026-02-09: Automation-grade crawl summary output (`--summary-json`) + documented stable exit codes. Evidence: `src/webcrawler/cli.py`, `src/webcrawler/crawler.py`, `tests/test_cli_summary_json.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `4cd0f87`.
- [x] 2026-02-09: URL allow/deny filters (`--include-regex`, `--exclude-regex`) applied to normalized URLs. Evidence: `src/webcrawler/cli.py`, `src/webcrawler/crawler.py`, `tests/test_cli_url_filters.py`, `README.md`, `make lint`, `make test`. Commit: `f864a1f`.
- [x] 2026-02-09: Python 3 crawler CLI + modular package (`src/webcrawler/*`, `pyproject.toml`, `webcrawler`). Evidence: `tests/test_crawl_integration.py`, `tests/test_urltools.py`, `make lint`, `make test`. Commits: `f6b2d7d`, `0eb1f7c`.
- [x] 2026-02-09: Politeness + reliability baseline (robots.txt obey by default, per-host delay knob, bounded retries, manual redirect handling, URL normalization/dedupe). Evidence: `src/webcrawler/crawler.py`, `src/webcrawler/urltools.py`. Commits: `f6b2d7d`.
- [x] 2026-02-09: CI for lint + tests (GitHub Actions). Evidence: `.github/workflows/ci.yml`. Commit: `0eb1f7c`.
- [x] 2026-02-09: README aligned to current behavior. Evidence: `README.md`. Commit: `0eb1f7c`.

## Insights
### Bounded Market Scan (Expectations)
Common baseline expectations for production crawlers/scrapers in this segment:
- Politeness: obey `robots.txt`, per-host pacing, and crawl delay where applicable.
- Reliability: bounded retries with backoff on transient 5xx/timeout conditions.
- Crawl control: depth/page limits, allowed domains, canonical URL normalization, redirect handling.
- Developer UX: clear CLI flags, structured logs, and structured outputs (JSONL/CSV) for downstream consumption.
- Long runs: pause/resume or checkpointing to avoid losing progress.

### Gap Map (High Level)
- Missing: concurrency (per-host caps) and a hop-based `--max-depth`.
- Weak: canonicalization beyond regex filters and query-param stripping (for example canonical link tag support).
- Parity: robots obey + pacing knobs, retry/backoff, structured outputs, resume/checkpointing, sitemap seeding.
- Differentiator: intentionally small, automation-friendly CLI with optional "secret flag" extraction and a stable summary JSON.

Sources (untrusted; for feature expectation only):
```text
https://docs.scrapy.org/en/latest/topics/autothrottle.html
https://docs.scrapy.org/en/latest/topics/settings.html#std-setting-ROBOTSTXT_OBEY
https://docs.scrapy.org/en/latest/topics/downloader-middleware.html?highlight=RetryMiddleware#retrymiddleware
https://docs.scrapy.org/en/latest/topics/feed-exports.html
https://docs.scrapy.org/en/latest/topics/spiders.html#sitemapspider
https://doc.scrapy.org/en/master/topics/jobs.html
https://crawler.archive.org/heritrix.html
https://www.gnu.org/software/wget/manual/wget.html#Recursive-Retrieval-Options
https://www.gnu.org/software/wget/manual/html_node/Logging-and-Input-File-Options.html
https://www.gnu.org/software/wget/manual/html_node/Download-Options.html
https://www.gnu.org/software/wget/manual/html_node/Exit-Status.html
https://docs.python.org/3/library/urllib.robotparser.html
https://www.sitemaps.org/protocol.html
```

## Notes
- This file is maintained by the autonomous clone loop.
