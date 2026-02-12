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

### 2026-02-12T20:01:43Z | Codex execution failure
- Date: 2026-02-12T20:01:43Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-2.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:05:09Z | Codex execution failure
- Date: 2026-02-12T20:05:09Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-3.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:08:39Z | Codex execution failure
- Date: 2026-02-12T20:08:39Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-4.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:12:06Z | Codex execution failure
- Date: 2026-02-12T20:12:06Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-5.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:15:38Z | Codex execution failure
- Date: 2026-02-12T20:15:38Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-6.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:19:06Z | Codex execution failure
- Date: 2026-02-12T20:19:06Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-7.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:22:35Z | Codex execution failure
- Date: 2026-02-12T20:22:35Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-8.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:26:13Z | Codex execution failure
- Date: 2026-02-12T20:26:13Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-9.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:29:44Z | Codex execution failure
- Date: 2026-02-12T20:29:44Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-10.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:33:12Z | Codex execution failure
- Date: 2026-02-12T20:33:12Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-11.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:36:41Z | Codex execution failure
- Date: 2026-02-12T20:36:41Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-12.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:40:10Z | Codex execution failure
- Date: 2026-02-12T20:40:10Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-13.log
- Commit: pending
- Confidence: medium

### 2026-02-12T20:43:37Z | Codex execution failure
- Date: 2026-02-12T20:43:37Z
- Trigger: Codex execution failure
- Impact: Repo session did not complete cleanly
- Root Cause: codex exec returned a non-zero status
- Fix: Captured failure logs and kept repository in a recoverable state
- Prevention Rule: Re-run with same pass context and inspect pass log before retrying
- Evidence: pass_log=logs/20260212-101456-Web-Crawler-Scraper-cycle-14.log
- Commit: pending
- Confidence: medium
