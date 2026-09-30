---
name: git-workflow
description: >
  Cisco IQ / CIQ monorepo git workflow — CHANGELOG.md mandatory entry rule,
  commit message format with CXP-XXXXX ticket reference, branch naming, and
  pre-commit hook failure recovery (black, flake8, mypy).
  Use this skill whenever the user asks to: commit changes, create a branch,
  push a PR, write a commit message, update the changelog, fix a pre-commit
  failure, deal with flake8 / black / mypy errors from hooks, or stage files.
  Also trigger when the user says "I'm done with a change" or "ready to commit"
  without having updated CHANGELOG.md.
---

# Git Workflow — CIQ Monorepo

## MANDATORY: CHANGELOG.md must be updated on every code change

**This is a hard rule in CLAUDE.md** — not optional.

Every session where any file in the repo is modified must include a
CHANGELOG.md entry at the repo root. The agent must:

1. Check whether `CHANGELOG.md` was modified in the current session.
2. If it was **not** modified, stop and prompt the user to add an entry
   **before** creating the commit.
3. Only proceed with the commit after the entry is added.

### Entry format

```
## YYYY-MM-DD

### <Project/Component>
- <Brief description of what changed> [CXP-XXXXX if applicable]
```

**Examples:**

```markdown
## 2026-06-05

### configbp-ai / agent
- Added retry logic to LLM factory for transient API errors [CXP-19735]

### assessment-unified-engine
- Fixed packager CronJob to respect IC_FILE_MAX_AGE_HOURS [CXP-19680]
```

### What counts as a change requiring an entry

Everything:
- New features, bug fixes, refactors
- Dependency updates (`uv.lock`, `package-lock.json`, `requirements*.txt`)
- Config changes (`helm/`, `.env.example`, `docker-compose.yml`)
- Schema changes (`baqs.json`, DBML files)
- Test additions or fixes

Does **not** require an entry:
- Changes only to this `CHANGELOG.md` itself
- Whitespace / comment-only changes that don't affect behaviour
- Changes to `JIRA/` ticket files (those are tracked in `JIRA/tickethistory.md` instead)

### CHANGELOG.md location

```
/Users/praspr/Documents/code_home/ciq/CHANGELOG.md
```

---

## Commit message format

```
<type>(<scope>): <imperative description> [CXP-XXXXX]
```

**Types:**
| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behaviour change |
| `test` | Add or update tests |
| `docs` | Documentation only |
| `chore` | Build, deps, config (no production code) |
| `perf` | Performance improvement |

**Scope** — the affected project or component:
- `configbp-ai` / `mcp-server` / `agent` / `a2a-server`
- `cbp-engine`
- `mini-maestro`
- `baqs` / `helm` / `lifecycle`

**Examples:**
```
feat(agent): add retry backoff for LLM transient errors [CXP-19735]
fix(cbp-engine): prevent duplicate findings on worker restart [CXP-19680]
chore(mini-maestro): bump spectral to 6.14 [CXP-19733]
refactor(mcp-server): extract Trino client into separate module
```

**CXP ticket reference:**
- Include `[CXP-XXXXX]` when the commit is directly traceable to a JIRA ticket.
- Omit only for pure housekeeping commits with no JIRA traceability.
- The ticket number goes at the end of the subject line.

---

## Branch naming

```
<type>/CXP-XXXXX-short-slug
```

Examples:
```bash
git checkout -b feat/CXP-19735-deep-insights-personalized-view
git checkout -b fix/CXP-19680-cli-guidance-empty-response
git checkout -b chore/no-ticket-bump-spectral
```

- `type` matches the commit message type above.
- `short-slug` is kebab-case, ≤ 5 words.
- When there is no JIRA ticket, use `no-ticket` in place of `CXP-XXXXX`.

---

## Pre-commit hook failures

The project uses `pre-commit` with three gates that run automatically on
`git commit`. When any gate fails, the commit is aborted. Fix the issue,
re-stage, and commit again.

### How to run all hooks manually (before committing)

```bash
cd /Users/praspr/Documents/code_home/ciq
pre-commit run --all-files
```

Or for staged files only:
```bash
pre-commit run
```

---

### Gate 1 — black (auto-formatter)

**What it checks:** Python source is formatted to black's standard (88-char lines, double quotes, consistent whitespace).

**Failure output example:**
```
black....................................................................Failed
- hook id: black
- files were modified by this hook
reformatted src/cbp_engine/core/worker.py
```

**Recovery:**
1. Black auto-fixes the files on failure — they're already reformatted.
2. Just re-stage and commit:
   ```bash
   git add -u
   git commit -m "..."
   ```
3. If you want to pre-empt the failure:
   ```bash
   black src/                     # configbp-ai services: run inside the service dir
   black src/cbp_engine/          # cbp-engine
   ```

**Black version:** `26.3.1` (pinned in project)

---

### Gate 2 — flake8 (linter — strict gate)

**What it checks:** PEP 8 compliance, unused imports, undefined names, complexity.

**Failure output example:**
```
flake8...................................................................Failed
- hook id: flake8
- exit code: 1
src/cbp_engine/core/worker.py:42:1: F401 'os' imported but unused
src/cbp_engine/core/worker.py:87:80: E501 line too long (92 > 88 characters)
```

**Recovery per error type:**

| Code | Meaning | Fix |
|------|---------|-----|
| `F401` | Unused import | Remove the import |
| `E501` | Line too long | black handles this — run black first |
| `F811` | Redefined name | Remove duplicate def/import |
| `F821` | Undefined name | Add missing import or fix typo |
| `W291`/`W293` | Trailing whitespace | black handles this |
| `E302`/`E303` | Wrong blank lines | black handles this |

For most `E` codes (whitespace/formatting): run `black` first, then re-check flake8.
For `F` codes (logic): fix the actual code.

**Run flake8 manually per service:**
```bash
# configbp-ai services (inside the service dir)
cd configbp-ai/agent && uv run flake8 src/

# cbp-engine
cd assessment-unified-engine && flake8 src/

# mini-maestro has no flake8 (TypeScript)
```

---

### Gate 3 — mypy (type checker)

**What it checks:** Static type correctness for Python source.

**Failure output example:**
```
mypy.....................................................................Failed
- hook id: mypy
- exit code: 1
src/cbp_engine/core/producer.py:54: error: Argument 1 to "process" has
  incompatible type "str | None"; expected "str"  [arg-type]
```

**Recovery approaches:**

1. **Fix the type properly** (preferred):
   ```python
   # Before (mypy complains: str | None passed to str param)
   process(value)

   # After
   if value is not None:
       process(value)
   # or
   process(value or "default")
   ```

2. **Use type: ignore for external/unavoidable cases** (last resort):
   ```python
   process(value)  # type: ignore[arg-type]
   ```
   Add a comment explaining why.

3. **Add missing type stubs** for third-party libraries:
   ```bash
   uv add --dev types-<package>  # e.g., types-requests
   ```

**Run mypy manually per service:**
```bash
cd configbp-ai/agent       && uv run mypy src/
cd configbp-ai/mcp-server  && uv run mypy src/
cd configbp-ai/a2a-server  && uv run mypy src/
cd assessment-unified-engine && python -m mypy src/
```

---

## Recommended commit workflow

```bash
# 1. Stage your changes
git add <specific files>   # prefer specific files over git add -A

# 2. Verify CHANGELOG.md is updated (mandatory)
git diff --name-only HEAD | grep CHANGELOG.md || echo "⚠️  Update CHANGELOG.md first!"

# 3. Run pre-commit manually to catch failures early
pre-commit run

# 4. Commit
git commit -m "feat(agent): add retry logic for LLM errors [CXP-19735]"
```

If the commit is blocked by a pre-commit failure, follow the recovery steps
for that gate above, then re-stage modified files and retry the commit.

---

## When to update this skill

Update when any of these change in the repo:
- CLAUDE.md commit conventions or CHANGELOG.md format
- Pre-commit hook configuration (`.pre-commit-config.yaml`)
- black version or config (`pyproject.toml`)
- flake8 rules or config (`setup.cfg` / `tox.ini` / `.flake8`)
- mypy config (`mypy.ini` / `pyproject.toml`)
- Branch naming conventions
