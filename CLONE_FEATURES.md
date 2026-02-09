# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration

## Candidate Features To Do

### Selected For This Session (Cycle 1)
- [ ] **P0: Port `webcrawler` to Python 3 + modern CLI** (Impact 5, Effort 3, Fit 5, Diff 2, Risk 2, Conf 5)
  - Remove hardcoded target, add `--start-url`, `--allowed-domain`, `--max-pages`, `--timeout`, `--user-agent`.
  - Keep backward-compatible `./webcrawler USER PASS` path via explicit options.
- [ ] **P0: Reliability: retries/backoff, redirect handling, and rate limiting** (Impact 5, Effort 3, Fit 5, Diff 2, Risk 2, Conf 4)
  - Avoid infinite loops on 5xx; add bounded retries.
  - Respect `robots.txt` by default; allow opt-out for controlled environments.
- [ ] **P0: URL normalization + dedupe + same-origin filtering** (Impact 4, Effort 2, Fit 5, Diff 2, Risk 2, Conf 5)
  - Normalize fragments, resolve relative links, avoid re-crawling.
- [ ] **P0: Add test + lint baseline** (Impact 5, Effort 3, Fit 5, Diff 2, Risk 2, Conf 4)
  - Local integration test with a tiny HTTP server fixture.
  - `ruff` + `pytest` run via `make test` / `make lint`.
- [ ] **P0: Add GitHub Actions CI** (Impact 4, Effort 2, Fit 5, Diff 1, Risk 1, Conf 4)
  - Run `ruff` and `pytest` on pushes to `main`.
- [ ] **P0: Update README to match behavior** (Impact 4, Effort 2, Fit 5, Diff 1, Risk 1, Conf 5)
  - Python 3 requirements; usage examples; troubleshooting.

### Candidate Backlog (Not Selected Yet)
- [ ] **P1: Structured outputs** (Impact 3, Effort 2, Fit 4, Diff 2, Risk 1, Conf 4)
  - `--out urls.jsonl` and `--out flags.txt` modes.
- [ ] **P1: Persistence/resume** (Impact 4, Effort 4, Fit 4, Diff 3, Risk 3, Conf 3)
  - Save frontier/visited to disk for long crawls.
- [ ] **P2: Concurrency + polite throttling** (Impact 3, Effort 4, Fit 3, Diff 2, Risk 3, Conf 3)
  - Optional parallel fetch with per-host limits.
- [ ] **P2: Extraction rules engine** (Impact 3, Effort 4, Fit 3, Diff 4, Risk 3, Conf 2)
  - CSS/XPath selectors via config file.

## Implemented

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
