# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do

- [ ] **P1: Structured outputs** (Impact 3, Effort 2, Fit 4, Diff 2, Risk 1, Conf 4)
  - `--out urls.jsonl` and `--out flags.txt` modes.
- [ ] **P1: Persistence/resume** (Impact 4, Effort 4, Fit 4, Diff 3, Risk 3, Conf 3)
  - Save frontier/visited to disk for long crawls.
- [ ] **P2: Concurrency + polite throttling** (Impact 3, Effort 4, Fit 3, Diff 2, Risk 3, Conf 3)
  - Optional parallel fetch with per-host limits.
- [ ] **P2: Extraction rules engine** (Impact 3, Effort 4, Fit 3, Diff 4, Risk 3, Conf 2)
  - CSS/XPath selectors via config file.

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
- Developer UX: clear CLI flags, structured logs, and testable behavior.

Sources (untrusted; for feature expectation only):
```text
https://docs.scrapy.org/en/latest/topics/autothrottle.html
https://docs.scrapy.org/en/latest/topics/settings.html#std-setting-ROBOTSTXT_OBEY
https://docs.scrapy.org/en/latest/topics/downloader-middleware.html?highlight=RetryMiddleware#retrymiddleware
https://crawler.archive.org/heritrix.html
https://www.gnu.org/software/wget/manual/wget.html#Recursive-Retrieval-Options
https://docs.python.org/3/library/urllib.robotparser.html
```

## Notes
- This file is maintained by the autonomous clone loop.
