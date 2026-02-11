# Project Memory

## Objective
- Keep Web-Crawler-Scraper production-ready. Current focus: webcrawler. Find the highest-impact pending work, implement it, test it, and push to main.

## Architecture Snapshot
- CLI entrypoint: `webcrawler` (console script via `pyproject.toml`) and repo-local wrapper `./webcrawler`.
- Package layout: `src/webcrawler/` with `cli.py`, `crawler.py`, `sitemaps.py`, `state.py`, `urltools.py`.
- Crawl engine basics:
  - Frontier: FIFO queue + normalized URL dedupe.
  - Politeness: robots.txt obeyed by default; optional per-host delay; Crawl-delay hint parsing (best-effort).
  - Reliability: bounded retries/backoff via `requests` + `urllib3.Retry`; optional crawl-level exception retries; optional HTML response size cap; manual 3xx redirect enqueue; hardened sitemap XML parser defaults with bounded sitemap fetch limits.
  - Outputs: optional JSONL fetch event stream (`--out-urls`) and line-based flags output (`--out-flags`).
  - Canonical handling: optional `--respect-canonical` to suppress duplicate link expansion when canonical target is already seen.
  - Persistence: optional `--state` checkpointing + `--resume`.

## Open Problems
- No concurrency (single-threaded fetch loop).

## Recent Decisions
- Template: YYYY-MM-DD | Decision | Why | Evidence (tests/logs) | Commit | Confidence (high/medium/low) | Trust (trusted/untrusted)
- 2026-02-11 | Add opt-in canonical hint handling (`--respect-canonical`) | Canonical hints are a common de-duplication signal; respecting them (without forcing global drop behavior) reduces duplicate frontier growth on URL-variant-heavy sites | `make lint`, `make test`, `make smoke`, new canonical tests, GitHub Actions CI success | 13f0ea7 | high | trusted
- 2026-02-11 | Harden sitemap parsing and expose sitemap safety limits in CLI | Sitemap inputs are untrusted and can be deeply nested/large; safe parser defaults and explicit max-sitemap/max-bytes controls improve reliability and safety | `make lint`, `make test`, `make smoke`, new nested/gzip sitemap tests, GitHub Actions CI success | 13f0ea7 | high | trusted
- 2026-02-11 | Add fail-fast validation for numeric CLI controls | Invalid automation inputs should fail early with usage exit code instead of producing undefined runtime behavior | `make lint`, `make test`, `make smoke`, new CLI validation tests, GitHub Actions CI success | 13f0ea7 | high | trusted
- 2026-02-11 | Refresh bounded market scan for crawler feature expectations | Reconfirmed baseline expectations around concurrency controls, robots compliance, retries, canonical handling, and sitemap guardrails from comparable tooling docs | bounded web scan links captured in `CLONE_FEATURES.md` insights | n/a | medium | untrusted
- 2026-02-10 | Add response size cap (`--max-body-bytes`) | Bounding HTML body size prevents pathological memory/time usage on large pages while keeping fetch events and crawl progress intact | `make lint`, `make test`, `make smoke`, new max-body-bytes test, GitHub Actions CI success | c60792f | high | trusted
- 2026-02-10 | Add retry-on-exception (`--exception-retries`) | Transient connection/timeout failures can recover later; bounded re-enqueue improves crawl completeness without risking infinite loops | `make lint`, `make test`, `make smoke`, new exception retry test, GitHub Actions CI success | c60792f | high | trusted
- 2026-02-10 | Add `--max-depth` hop limit + persist hop depths in state v2 | Depth limits are a core crawl control to bound traversal; persisting depth preserves semantics across resume/checkpoint runs | `make lint`, `make test`, `make smoke`, new max-depth + sitemap depth tests, GitHub Actions CI success | 6600ade | high | trusted
- 2026-02-10 | Add `--robots-fail-closed` hard politeness mode | Some controlled environments prefer failing closed when robots.txt is unavailable, preventing accidental non-compliance | `make lint`, `make test`, new robots fail-closed test, GitHub Actions CI success | 6600ade | high | trusted
- 2026-02-09 | Add sitemap seeding (`--sitemap-url`, `--sitemap-auto`, `--sitemap-from-robots`) | Helps find pages that are not discoverable via link traversal; keeps crawler useful on sites with sparse navigation | `make lint`, `make test`, `make smoke`, new sitemap seeding tests, GitHub Actions CI success | 7e96dc2 | high | trusted
- 2026-02-09 | Add optional tracking-param stripping (`--strip-query-param`, `--strip-utm`) applied before dedupe | Reduces duplicated crawl work caused by analytics query params; improves crawl coverage under a fixed max-pages budget | `make lint`, `make test`, `make smoke`, new CLI + urltools tests, GitHub Actions CI success | 603971c | high | trusted
- 2026-02-09 | Port crawler to Python 3 with a modular CLI + package | Python 2-only script was not runnable in current environments; modern CLI enables safe crawl controls and testability | `make lint`, `make test`, local CLI smoke crawl (flags extracted) | f6b2d7d, 0eb1f7c | high | trusted
- 2026-02-09 | Add structured outputs + persistence/resume + improved Crawl-delay parsing | Automation needs file outputs; long crawls need checkpoint/resume; Crawl-delay parsing needed basic correctness for multi-User-agent groups | `make lint`, `make test`, `make smoke`, new tests for CLI outputs/resume and Crawl-delay parsing | eef8325, 2c76e2f | high | trusted
- 2026-02-09 | Add machine-readable crawl summary (`--summary-json`) + document stable exit codes | Makes CLI automation-friendly without breaking flag-extraction stdout contract | `make lint`, `make test`, `make smoke`, new tests for summary output | 4cd0f87 | high | trusted
- 2026-02-09 | Add URL allow/deny regex filters (`--include-regex`, `--exclude-regex`) | Common crawler control needed to target sections and avoid irrelevant pages | `make lint`, `make test`, new tests for include/exclude behavior | f864a1f | high | trusted

## Mistakes And Fixes
- Template: YYYY-MM-DD | Issue | Root cause | Fix | Prevention rule | Commit | Confidence
- 2026-02-11 | Initial lint failure after feature implementation (`E501`, `UP012`) | New tests and canonical logic were added quickly without a final lint pass before first verification run | Wrapped long lines and removed redundant `encode("utf-8")`; reran full lint/test/smoke | Run `make lint` immediately after adding or modifying tests, before full test run | 13f0ea7 | high

## Known Risks
- Login helper is intentionally minimal and may not work for complex auth flows (multi-step, JS, MFA, CAPTCHA).
- Requests-based crawler does not execute JavaScript (no headless browser rendering).

## Next Prioritized Tasks
- P1: Concurrency with per-host caps + politeness defaults.
- P2: HTTP cache / conditional GET.
- P2: Content-type allow/deny controls for parsing/extraction.

## Verification Evidence
- Template: YYYY-MM-DD | Command | Key output | Status (pass/fail)
- 2026-02-11 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-11 | `. .venv/bin/activate && make test` | `32 passed` | pass
- 2026-02-11 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-11 | `gh run watch 21894312268 --interval 5 --exit-status` | `CI completed success (python 3.11/3.12/3.13)` | pass
- 2026-02-10 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-10 | `. .venv/bin/activate && make test` | `24 passed` | pass
- 2026-02-10 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-10 | `gh run watch 21853158608 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-10 | `gh run watch 21853209255 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-10 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-10 | `. .venv/bin/activate && make test` | `22 passed` | pass
- 2026-02-10 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-10 | `gh run watch 21847423285 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-10 | `gh run watch 21847476705 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `4 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `stdout_flags=['SMOKE_ONE','SMOKE_TWO'] exit_code=0` | pass
- 2026-02-09 | `gh run watch 21816332997 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `9 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `stdout_flags=['SMOKE_ONE','SMOKE_TWO'] exit_code=0` | pass
- 2026-02-09 | `gh run watch 21824043405 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `gh run watch 21831982485 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `11 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21832003543 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `13 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21832092071 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `gh run watch 21832159506 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `16 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21841017448 --interval 5 --exit-status` | `CI completed success` | pass
- 2026-02-09 | `. .venv/bin/activate && make lint` | `All checks passed!` | pass
- 2026-02-09 | `. .venv/bin/activate && make test` | `19 passed` | pass
- 2026-02-09 | `. .venv/bin/activate && make smoke` | `exit_code=0 stdout_flags=['SMOKE_ONE','SMOKE_TWO']` | pass
- 2026-02-09 | `gh run watch 21841156652 --interval 5 --exit-status` | `CI completed success` | pass

## Historical Summary
- Keep compact summaries of older entries here when file compaction runs.
