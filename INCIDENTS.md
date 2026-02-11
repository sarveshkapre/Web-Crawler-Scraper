# Incidents And Learnings

## Entry Schema
- Date
- Trigger
- Impact
- Root Cause
- Fix
- Prevention Rule
- Evidence
- Commit
- Confidence

## Entries
- Date: 2026-02-11
  Trigger: Local lint gate failed (`ruff`) during verification of canonical/sitemap feature batch.
  Impact: Release validation paused until style/quality issues were fixed.
  Root Cause: Long lines and redundant `encode("utf-8")` usage introduced while adding new tests and crawl logic.
  Fix: Wrapped long lines, removed redundant encoding arguments, reran `make lint`, `make test`, and `make smoke`.
  Prevention Rule: Run `make lint` immediately after test/code edits before full verification runs and before commit.
  Evidence: `make lint` pass, `make test` pass (`32 passed`), `make smoke` pass.
  Commit: 13f0ea7
  Confidence: high
