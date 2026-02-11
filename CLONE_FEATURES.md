# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do

- [ ] **P1 [Selected Next]: Concurrency + polite throttling** (Impact 5, Effort 5, Fit 5, Diff 2, Risk 4, Conf 2)
  - Optional parallel fetch with per-host caps + backpressure while preserving robots/pacing semantics.
- [ ] **P2: HTTP cache / conditional GET** (Impact 4, Effort 4, Fit 4, Diff 2, Risk 3, Conf 2)
  - Support `ETag`/`If-Modified-Since` to reduce refetching on repeated crawls.
- [ ] **P2: Content-type allow/deny for parsing** (Impact 3, Effort 2, Fit 4, Diff 1, Risk 2, Conf 4)
  - Add parse/extraction allowlist/denylist by content type while still recording fetch events.
- [ ] **P2: Duplicate-content suppression** (Impact 3, Effort 3, Fit 3, Diff 2, Risk 2, Conf 3)
  - Optional HTML body hashing to avoid processing near-identical pages under multiple URLs.
- [ ] **P2: Resume integrity checks** (Impact 3, Effort 2, Fit 4, Diff 1, Risk 2, Conf 4)
  - Warn/fail on resume when critical crawl-shaping flags changed incompatibly (host filters/regex/depth).
- [ ] **P2: Structured stats expansion** (Impact 3, Effort 2, Fit 4, Diff 1, Risk 1, Conf 4)
  - Add status-code buckets, bytes, and retry counters to `--summary-json`.
- [ ] **P2: Retry policy tuning knobs** (Impact 3, Effort 2, Fit 4, Diff 1, Risk 2, Conf 3)
  - Expose retry status-forcelist and per-error retry caps for stricter production control.
- [ ] **P2: Sitemap seed tests for nested/gzip/error paths** (Impact 3, Effort 2, Fit 4, Diff 1, Risk 1, Conf 4)
  - Add tests for nested sitemap indexes, `.gz`, and failure accounting.
- [ ] **P3: Extraction rules engine** (Impact 3, Effort 4, Fit 3, Diff 4, Risk 3, Conf 2)
  - CSS selectors via config file; emit extracted fields to JSONL.
- [ ] **P3: Optional JS rendering mode** (Impact 3, Effort 5, Fit 2, Diff 4, Risk 4, Conf 2)
  - Optional Playwright-powered fetcher for JS-heavy pages (explicit opt-in).
- [ ] **P3: robots.txt cache TTL for long crawls** (Impact 2, Effort 2, Fit 3, Diff 1, Risk 2, Conf 3)
  - Periodically refresh robots rules for very long-running crawls.
- [ ] **P3: Domain fairness scheduler** (Impact 3, Effort 3, Fit 3, Diff 2, Risk 3, Conf 2)
  - Round-robin by host to avoid starvation when one domain dominates the frontier.
- [ ] **P3: Smoke test in CI** (Impact 2, Effort 2, Fit 3, Diff 1, Risk 1, Conf 4)
  - Add `make smoke` or equivalent local server smoke path to CI for higher end-to-end confidence.
- [ ] **P3: Benchmark harness for crawl throughput** (Impact 2, Effort 3, Fit 3, Diff 2, Risk 2, Conf 3)
  - Add repeatable local benchmark script for perf regression checks.

## Implemented
- [x] 2026-02-11: Canonical-link hint support (`--respect-canonical`) to suppress duplicate link expansion when canonical target is already seen, while still preserving page fetch and extraction behavior. Evidence: `src/webcrawler/crawler.py`, `src/webcrawler/cli.py`, `tests/test_canonical_links.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `13f0ea7`.
- [x] 2026-02-11: Sitemap seeding hardening with safe XML parser defaults + explicit limits (`--sitemap-max-sitemaps`, `--sitemap-max-bytes`) and nested/gzip sitemap coverage tests. Evidence: `src/webcrawler/sitemaps.py`, `src/webcrawler/cli.py`, `tests/test_sitemaps.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `13f0ea7`.
- [x] 2026-02-11: CLI numeric validation hardening for crawl and sitemap controls (fail-fast usage errors). Evidence: `src/webcrawler/cli.py`, `tests/test_cli_validation.py`, `make lint`, `make test`, `make smoke`. Commit: `13f0ea7`.
- [x] 2026-02-10: Response size cap (`--max-body-bytes`) to bound HTML parsing/extraction on very large pages (skip parsing beyond cap). Evidence: `src/webcrawler/crawler.py`, `src/webcrawler/cli.py`, `tests/test_max_body_bytes.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `c60792f`.
- [x] 2026-02-10: Retry-on-exception with cap (`--exception-retries`) to re-enqueue transient fetch failures without an HTTP response. Evidence: `src/webcrawler/crawler.py`, `src/webcrawler/cli.py`, `tests/test_exception_retries.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `c60792f`.
- [x] 2026-02-10: Max depth / hop limit (`--max-depth`) to bound traversal by link distance from seeds (start URLs and sitemap seeds count as depth 0). Evidence: `src/webcrawler/crawler.py`, `src/webcrawler/cli.py`, `src/webcrawler/state.py`, `tests/test_cli_max_depth.py`, `tests/test_cli_sitemap_seeding.py`, `README.md`, `make lint`, `make test`, `make smoke`. Commit: `6600ade`.
- [x] 2026-02-10: Hard politeness mode (`--robots-fail-closed`) to fail closed when `robots.txt` can't be fetched (default remains fail-open). Evidence: `src/webcrawler/crawler.py`, `src/webcrawler/cli.py`, `tests/test_robots_fail_closed.py`, `README.md`, `make lint`, `make test`. Commit: `6600ade`.
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
- Reliability: bounded retries with backoff on transient 5xx/timeout conditions and safe parsing defaults for untrusted crawl inputs.
- Crawl control: depth/page limits, allowed domains, canonical URL normalization, redirect handling, and configurable sitemap guards.
- Developer UX: clear CLI flags, structured logs, and structured outputs (JSONL/CSV) for downstream consumption.
- Long runs: pause/resume or checkpointing to avoid losing progress.

### Gap Map (High Level)
- Missing: concurrency (per-host caps).
- Weak: HTTP freshness/cache controls (`ETag`/`If-Modified-Since`) and host fairness scheduling.
- Parity: robots obey + pacing knobs, retry/backoff, response size caps, canonical hint handling, structured outputs, resume/checkpointing, sitemap seeding.
- Differentiator: intentionally small, automation-friendly CLI with optional "secret flag" extraction, stable summary JSON, and opt-in canonical dedupe behavior.

Sources (untrusted; for feature expectation only):
```text
https://docs.scrapy.org/en/latest/topics/autothrottle.html
https://docs.scrapy.org/en/latest/topics/settings.html#concurrent-requests-per-domain
https://docs.scrapy.org/en/latest/topics/settings.html#std-setting-ROBOTSTXT_OBEY
https://docs.scrapy.org/en/latest/topics/downloader-middleware.html?highlight=RetryMiddleware#retrymiddleware
https://docs.scrapy.org/en/latest/topics/settings.html#download-maxsize
https://docs.scrapy.org/en/latest/topics/spiders.html#sitemapspider
https://crawlee.dev/js/docs/guides/respect-robots-txt-file
https://crawlee.dev/js/docs/guides/scaling-crawlers
https://docs.firecrawl.dev/rate-limits
https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
https://www.sitemaps.org/protocol.html
```

## Notes
- This file is maintained by the autonomous clone loop.
