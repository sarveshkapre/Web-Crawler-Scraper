# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do

- [ ] **P1: Structured outputs (URLs + flags)** (Impact 5, Effort 2, Fit 5, Diff 2, Risk 2, Conf 4)
  - Add `--out-urls urls.jsonl` (JSONL events) and `--out-flags flags.txt` (one per line).
  - Add `--append-output` to support resuming pipelines without clobbering outputs.
- [ ] **P1: Persistence/resume for long crawls** (Impact 5, Effort 4, Fit 5, Diff 3, Risk 3, Conf 3)
  - Add `--state state.json` + `--resume` to load/save frontier + visited (checkpointing).
  - Save on clean exit and on Ctrl-C.
- [ ] **P1: Automation-grade exit codes + summary** (Impact 4, Effort 2, Fit 5, Diff 2, Risk 1, Conf 4)
  - Document stable exit codes (usage error vs runtime error vs Ctrl-C).
  - Add `--summary-json` (print crawl stats to stdout/stderr deterministically).
- [ ] **P2: Sitemap seeding** (Impact 3, Effort 3, Fit 4, Diff 2, Risk 2, Conf 3)
  - Add `--sitemap-url` (repeatable) and/or auto-discover `/sitemap.xml` when same-host.
- [ ] **P2: URL allow/deny filters** (Impact 4, Effort 3, Fit 4, Diff 2, Risk 2, Conf 3)
  - Add `--include-regex` / `--exclude-regex` applied to normalized URLs.
- [ ] **P2: Concurrency + polite throttling** (Impact 4, Effort 4, Fit 4, Diff 2, Risk 3, Conf 3)
  - Optional parallel fetch with per-host caps + backpressure; keep robots/pacing correct.
- [ ] **P2: Better robots Crawl-delay parsing** (Impact 2, Effort 2, Fit 4, Diff 1, Risk 1, Conf 4)
  - Handle multi-line `User-agent:` groups more correctly; add unit tests.
- [ ] **P3: HTTP cache / conditional GET** (Impact 3, Effort 4, Fit 3, Diff 2, Risk 3, Conf 2)
  - Support `ETag`/`If-Modified-Since` to reduce refetching on repeated crawls.
- [ ] **P3: Extraction rules engine** (Impact 3, Effort 4, Fit 3, Diff 4, Risk 3, Conf 2)
  - CSS selectors via config file; emit extracted fields to JSONL.
- [ ] **P3: Optional JS rendering mode** (Impact 3, Effort 5, Fit 2, Diff 4, Risk 4, Conf 2)
  - Optional Playwright-powered fetcher for JS-heavy pages (explicit opt-in).

## Implemented
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

Sources (untrusted; for feature expectation only):
```text
https://docs.scrapy.org/en/latest/topics/autothrottle.html
https://docs.scrapy.org/en/latest/topics/settings.html#std-setting-ROBOTSTXT_OBEY
https://docs.scrapy.org/en/latest/topics/downloader-middleware.html?highlight=RetryMiddleware#retrymiddleware
https://docs.scrapy.org/en/latest/topics/feed-exports.html
https://doc.scrapy.org/en/master/topics/jobs.html
https://crawler.archive.org/heritrix.html
https://www.gnu.org/software/wget/manual/wget.html#Recursive-Retrieval-Options
https://www.gnu.org/software/wget/manual/html_node/Logging-and-Input-File-Options.html
https://www.gnu.org/software/wget/manual/html_node/Download-Options.html
https://docs.python.org/3/library/urllib.robotparser.html
```

## Notes
- This file is maintained by the autonomous clone loop.
