# SB Remediation Plan

Status: **Planned — not yet implemented.**
Source: deep read-only code review of `sb` (core + domain services + web).
Scope decision: **full plan**, including the higher-risk items (M1 migration
guard, M2 normalized ledger-refs table), an **actual access gate** on
write-capable MCP tools (M5), and **config-driven** personal paths (L4).

The review found **no critical bugs**. This plan is about hardening two
high-value security gaps first, then correctness/scaling, then hygiene. No
change may weaken the codebase's existing strengths: deterministic redaction,
append-only ledger integrity, validated-citation LLM fallbacks,
fresh-connection-per-call, and the read-only JIRA/Webex guarantees.

---

## Guiding principles

- **Preserve proven correctness.** Append-only triggers, redaction, PKCE,
  citation validation, and idempotent migrations are load-bearing. Every change
  ships with tests matching the existing patterns (per-rule redaction fixtures,
  migration tests, dual-write tests).
- **Measure before optimizing.** Performance work is explicitly **out of scope**
  here (the one reported concern is unmeasured). When revisited, profile first;
  the likely local hotspots are already captured as M1 and M2.
- **Full gate per phase.** `uv run pytest` in each affected service before moving
  on. The web app is untouched by this plan.
- **Commit convention:** conventional commits (`fix(core):`, `feat(core):`,
  `docs:`), no CXP tickets, clean human CHANGELOG entry (never commit the
  auto-generated ledger noise).

---

## Severity → item index

| ID | Severity | Title | Phase |
|----|----------|-------|-------|
| H1 | High | Expand secret redaction to modern token formats | 1 |
| H2 | High | Atomic CHANGELOG write (temp-file + `os.replace`) | 1 |
| M5 | Medium | Access gate on write-capable MCP tools | 1 |
| M4 | Medium | Cron robustness (dow=7, validation, DST note) | 2 |
| M1 | Medium | Per-process migration guard | 2 |
| M2 | Medium | Normalized `sb_ledger_refs` table + migration | 2 |
| L2 | Low | Validate JIRA key in `fetch_issue` | 2 |
| L1 | Low | Hash the token used as an LRU cache key | 3 |
| L3 | Low | Fix doc drift (schema version, counts, routes) | 3 |
| L4 | Low | Config-driven personal paths / emails | 3 |

---

## Phase 1 — Security hardening

Highest value, smallest surface. Ship this first as one focused branch.

### H1 — Expand secret redaction

**File:** `services/core/src/sb_core/ledger_redact.py`
**Why first:** redacted ledger entries dual-write to a git-tracked
`CHANGELOG.md` (`ledger_tools.py:106-118`). A missed token reaches git history.

**Current coverage:** AWS key, AWS secret, Bearer, JWT, basic-auth URL,
`UPPER_VAR=secret`, LangSmith, keyword-proximity long hex (`ledger_redact.py:19-43`).

**Gap:** common pasted credentials are not matched — GitHub, OpenAI, Slack,
Google API keys, Stripe, and bare `token: <value>` in prose.

**Changes (specific-first ordering preserved):**

- GitHub: `\bgh[pousr]_[A-Za-z0-9]{36,}\b` → `[REDACTED:GITHUB_TOKEN]`
- OpenAI: `\bsk-(?:proj-)?[A-Za-z0-9]{20,}\b` → `[REDACTED:OPENAI_KEY]`
- Slack: `\bxox[baprs]-[A-Za-z0-9-]{10,}\b` → `[REDACTED:SLACK_TOKEN]`
- Google API key: `\bAIza[0-9A-Za-z_\-]{35}\b` → `[REDACTED:GOOGLE_API_KEY]`
- Stripe: `\b(?:sk|rk)_live_[A-Za-z0-9]{24,}\b` → `[REDACTED:STRIPE_KEY]`
- Generic keyword+value: `(?i)(api[_-]?key|token|secret)\s*[:=]\s*['"]?<value>`
  — reuse the existing keyword-proximity style; **do not** add a blanket
  entropy scanner that would mangle prose.
- Bump `REDACTION_RULES_VERSION` → `2`. New rows stamp version 2; existing rows
  keep version 1 (correct provenance).

**Tests** (`tests/test_ledger_redact.py`):
- One positive + one negative fixture per new rule (match existing style).
- Update `test_rules_version_is_stamped` to `== 2`.
- **Over-redaction guards (critical):** assert a 40-char git SHA and a UUID are
  **not** redacted — these are the realistic false-positive risks.
- Integration: a GitHub/OpenAI token in `body` is scrubbed, and the dual-write
  path (`test_ledger_dualwrite.py`) writes the scrubbed form to the file.

**Risk:** Low. Additive rules; negative fixtures guard against over-redaction.

### H2 — Atomic CHANGELOG write

**File:** `services/core/src/sb_core/ledger_sync.py:114-138`
**Why:** `append_to_changelog` does `read_text → compute → write_text` under an
flock. The `write_text` is a direct overwrite — a crash/kill/disk-full mid-write
can **truncate the human-curated CHANGELOG**.

**Change:** inside `_locked(...)`, replace the direct `write_text` with
temp-file + `os.replace`, mirroring the proven pattern in `llm.py:109-115`:
write to `.{name}.{pid}.tmp` in the same directory, `os.replace(tmp, path)`,
unlink the temp on error. The flock still serializes writers; `os.replace`
makes the swap atomic on POSIX.

**Tests** (`tests/test_ledger_dualwrite.py`):
- Simulate a write failure (monkeypatch the temp write to raise) → original
  file is byte-intact and no `.tmp` residue remains.
- Normal append still produces the identical result as today.

**Risk:** Very low; mechanical, mirrors existing code.

### M5 — Access gate on write-capable MCP tools

**Files:** `services/core/src/sb_core/main.py` (host), plus a small shared
guard used by write tools (`ledger_tools.py`, `webex_post.py`, and the todos
write tools via their mount).
**Why:** anything that can reach `127.0.0.1:8787/mcp` currently gets full tool
access, including write-capable `todo_*`, `ledger_log`, `ledger_batch_log`,
`webex_post_message`. A malicious local page or process could drive these.

**Design (chosen: an actual gate, not docs-only):**

- Introduce a **local shared secret** (`SB_CORE_LOCAL_TOKEN`, auto-generated to
  `~/.local/share/sb/local_token` with `0o600` on first run if unset).
- Require the token (via a header, e.g. `X-SB-Local-Token`, or an MCP arg the
  host injects) **only for the write-capable subset**. Read tools stay open to
  preserve the localhost ergonomics.
- The dashboard and CLI read the token from the same file and attach it. The
  Vite dev proxy forwards it.
- Backward-compatibility switch: `SB_CORE_REQUIRE_LOCAL_TOKEN` (default on once
  harnesses are updated). Document a one-line opt-out for anyone who breaks.

**Rollout caution (important):** this can break existing harness/dashboard calls
if not perfectly matched. Sequence:
1. Land the token **issuance + read** plumbing (dashboard, CLI, proxy) with the
   requirement **off** (observe-only logging of which callers present it).
2. Flip the requirement on for write tools once logs show all legitimate callers
   attach it.
3. Keep the env opt-out documented.

**Tests:**
- Write tool rejects a call without/with a wrong token (401-equivalent MCP error).
- Write tool accepts a call with the correct token.
- Read tools are unaffected.
- Token file is created `0o600` and never logged.

**Risk:** Medium (can break callers). Mitigated by the staged off→observe→on rollout.

---

## Phase 2 — Correctness & scaling

Second branch. M1 and M2 are the riskier items — each gets its own commit with
dedicated tests.

### M4 — Cron robustness

**File:** `services/core/src/sb_core/scheduler.py:51-88`

- **`dow=7` as Sunday:** standard cron accepts both 0 and 7 for Sunday; the
  current `_parse_field` caps dow at high=6. Normalize `7 → 0` for the dow field
  (or in `cron_matches`). (Note: the existing `cron_matches` weekday remap at
  `scheduler.py:98` is already correct for 0–6.)
- **Fail loudly on bad fields:** `_parse_field` currently yields an empty set for
  out-of-range/typo'd values (e.g. minute `70`), silently making a schedule a
  no-op. Raise `ValueError("bad cron field: …")` instead.
- **DST:** `last_scheduled_at` walks local minutes; around DST transitions a
  naive-local comparison could theoretically double-fire or skip. Duplicate
  suppression already relies on `last_run_at` comparison
  (`run_due_schedules`, `scheduler.py:327-338`), which is correct. Add a comment
  documenting this and a characterization test around a known DST date.

**Tests** (`tests/test_scheduler.py`): `dow=7` matches Sunday; malformed field
raises; a DST-transition date does not double-fire given a prior `last_run_at`.

**Risk:** Low (`7`-as-Sunday and validation are additive; DST test is
characterization-only).

### M1 — Per-process migration guard

**File:** `services/core/src/sb_core/store/db.py:409-488`
**Why:** `connect()` runs full migrations on **every** call, and the codebase
opens a fresh connection per MCP tool call (`_get_conn()` everywhere). Each call
pays the bootstrap txn + version scan + `_ensure_required_columns` scan — a
per-request tax on the hot path.

**Change:** add a process-level set of resolved DB paths whose migrations have
already run this process; on subsequent `connect()` for the same path, skip the
migration run (still safe — migrations are idempotent — and still runs once per
process). Keep a `force`/env escape hatch so tests and schema changes can force a
re-run.

**Tests** (`tests/` db-focused):
- Fresh DB still fully migrates on first connect.
- Second `connect()` to the same path does not re-run the scan (assert via a
  spy/counter on `run_migrations`).
- `force=True` (or the env flag) re-runs it.
- Concurrent first-connect from two connections still succeeds.

**Risk:** Medium — touches the hot path. Mitigation: key the guard by resolved
path; preserve `_ensure_required_columns` on first-connect only; provide the
escape hatch.

### M2 — Normalized `sb_ledger_refs` table + migration

**Files:** `services/core/src/sb_core/store/db.py` (new migration `_m12`),
`services/core/src/sb_core/store/ledger.py` (`by_ref`, `open_threads`).
**Why:** `by_ref` and `open_threads` scan up to 2000/500 rows and filter `refs`
JSON in Python (`ledger/store.py:215-216, 250-252`). The ledger is append-only
and grows unbounded (plus scheduler noise). This degrades over time.

**Change:**

- New migration `_m12_ledger_refs` creating:
  ```sql
  CREATE TABLE IF NOT EXISTS sb_ledger_refs (
    ledger_id INTEGER NOT NULL,
    kind      TEXT    NOT NULL,
    value     TEXT    NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_ledger_refs_kv
    ON sb_ledger_refs(kind, value);
  CREATE INDEX IF NOT EXISTS idx_ledger_refs_lid
    ON sb_ledger_refs(ledger_id);
  ```
- Populate on insert. Prefer extending `append_ledger` to also insert ref rows
  (the ledger stays append-only; refs are derived child rows). Keep the
  append-only triggers on `sb_ledger` itself unchanged.
- **Backfill** existing rows inside the migration (parse each row's `refs` JSON
  once).
- Rewrite `by_ref`/`open_threads` to join `sb_ledger_refs` instead of scanning.

**Tests:**
- Migration backfills existing refs correctly.
- `by_ref` returns identical results to the old implementation on a fixture set.
- New inserts populate `sb_ledger_refs`.
- Append-only guarantee on `sb_ledger` is still enforced.

**Risk:** Medium — new migration + backfill + query rewrite. Mitigation: keep the
old Python-filter path available behind a flag during rollout; assert
equivalence in tests before removing it.

### L2 — Validate JIRA key in `fetch_issue`

**File:** `services/jira/src/sb_jira/atlassian_client.py:161-167`
**Why:** `fetch_issue` interpolates `key` into the URL path. `track_jira`
validates strictly (`tracking.py:13`), but `fetch_issue` is callable directly
without that guard. Read-only API limits impact; still, defense-in-depth.

**Change:** validate `key` against `^[A-Z][A-Z0-9]*-\d+$` (reuse the
`tracking.py` pattern) before building the URL; raise `ValueError` on mismatch.

**Tests** (jira tests): `fetch_issue("../myself")` raises before any HTTP call.

**Risk:** Low.

---

## Phase 3 — Hygiene & docs

Third branch. Low risk, quick.

### L1 — Hash the token used as an LRU cache key

**File:** `services/webex/src/sb_webex/client.py:259-267`
`_fetch_message_cached(token, message_id)` holds the bearer token as an
`lru_cache` key in process memory. Key on `sha256(token).hexdigest()` instead so
the secret isn't retained as a cache key. Behavior unchanged.

### L3 — Fix doc drift

**File:** `README.md` (and `docs/` where echoed).
- Schema version is **11** (`db.py` has 11 migrations), not 10.
- Re-verify the "76 tools / 20 prompts / 20 resources" counts against
  `GET /health` and update.
- `/attention` was removed from the sidebar navbar; update the routes/architecture
  notes accordingly (the page/route still exist, just unlinked).

### L4 — Config-driven personal paths / emails

**Files:** `services/core/src/sb_core/config.py:246-259` (`_SEED_PROJECTS`),
`services/jira/src/sb_jira/file_store.py:51-53` (`KNOWN_EMAILS`).
**Why:** hardcoded `~/Documents/code_home/{ciq,sb}` and `praspr@cisco.com` block
portability and put an email in source.

**Change:** move both behind config/env with the **current values as documented
defaults**, so behavior is identical for the current user but the repo is
portable and carries no personal email in source. Example: a
`SB_CORE_SEED_PROJECTS` config entry and a `known_emails` map in config.

**Tests:** defaults reproduce today's seed + email mapping; overrides take effect.

### Nits (fold in where touching the file)

- `ritual_tools.py` is 610 lines doing plan/wrap/standup/proposal — split by
  ritual if we're already editing it.
- Clearer cron error messages (covered by M4).

---

## Sequencing & verification

1. **Phase 1 (security)** — one branch. Full core suite + `test_ledger_*` + a
   manual `ledger_log` smoke confirming scrubbed CHANGELOG output. Ship first.
2. **Phase 2 (correctness/scaling)** — second branch. M1 and M2 each isolated in
   their own commit with dedicated tests; L2 and M4 alongside.
3. **Phase 3 (hygiene/docs)** — third branch.

Per phase: `cd services/core && uv run pytest`; each touched service runs its own
`pytest`. Commit with conventional messages and a clean human CHANGELOG entry;
never stage the auto-generated ledger noise.

## Explicitly out of scope

- **Performance / language rewrite.** Decision recorded separately: stay Python;
  no Rust/Go rewrite. The workload is I/O/network/LLM-bound. If performance is
  revisited, **profile first**; the likely local wins (M1, M2) are already in
  this plan.
