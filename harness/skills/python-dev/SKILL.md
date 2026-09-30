---
name: python-dev
description: >
  Python development patterns for the CIQ monorepo — uv vs pip service
  matrix, exact test/lint/format commands per service, dependency management,
  quality gate pipeline, and common failure recovery.
  Use this skill whenever the user asks to: run tests, add a dependency,
  sync uv, run pytest, fix flake8 / mypy / black errors, run the quality
  gate, update a lock file, install requirements, or work with any Python
  service in configbp-ai (agent, mcp_server, a2a_server) or
  assessment-unified-engine (cbp-engine).
  Also trigger when the user sees errors like: "uv: command not found",
  "401 on uv sync", "uv.lock conflict", "mypy error", "flake8 violation",
  "black reformatted", or "No module named ...".
---

# Python Development — CIQ Monorepo

## Service quick reference

| Service | Root Directory | Dep Manager | Python | Test Command |
|---------|---------------|-------------|--------|--------------|
| **agent** | `configbp-ai/agent/` | `uv` | 3.13 | `uv run pytest tests/ -v` |
| **mcp_server** | `configbp-ai/mcp_server/` | `uv` | 3.13 | `uv run pytest tests/ -v` |
| **a2a_server** | `configbp-ai/a2a_server/` | `uv` | 3.13 | `uv run pytest tests/ -v` |
| **cbp-engine** | `assessment-unified-engine/` | `pip` | 3.x | `make test` |
| **all configbp-ai** | `configbp-ai/` | — | — | `./scripts/run_all_tests.sh` |

---

## Quality gate pipeline (run in this order)

For each `uv`-based service (`agent`, `mcp_server`, `a2a_server`):

```bash
cd configbp-ai/<service-dir>

make format    # black 26.3.1 — auto-fixes formatting
make lint      # flake8 strict gate + complexity report
uv run mypy .  # type checking (not in Makefile — run manually)
make test      # pytest + coverage + JUnit XML → test-reports/
```

For `cbp-engine`:
```bash
cd assessment-unified-engine

black src/              # format
flake8 src/             # lint
python -m mypy src/     # type checking
make test               # pytest via Makefile
```

---

## uv patterns (configbp-ai services)

### Sync (initial setup or after lockfile changes)

```bash
cd configbp-ai/<service-dir>
uv sync --locked --group dev --python python3.13
```

**Artifactory credentials required** for `a2a_server` (private package).
Set before syncing:
```bash
export UV_INDEX_CISCO_ARTIFACTORY_USERNAME="<cisco-username>"
export UV_INDEX_CISCO_ARTIFACTORY_PASSWORD="<artifactory-api-token>"
```

### Add a production dependency

```bash
cd configbp-ai/<service-dir>
uv add <package-name>
```

### Add a dev-only dependency

```bash
cd configbp-ai/<service-dir>
uv add --dev <package-name>
```

### Upgrade a specific package

```bash
cd configbp-ai/<service-dir>
uv lock --upgrade-package <package-name>
uv sync --locked --group dev --python python3.13
```

### Upgrade all packages (carefully)

```bash
uv lock --upgrade
uv sync --locked --group dev --python python3.13
```

### Check what's installed

```bash
uv pip list
```

---

## pip patterns (cbp-engine)

```bash
cd assessment-unified-engine

# Initial setup
python -m venv venv && source venv/bin/activate
make install-reqs        # pip install -r requirements.txt -e .
make install-test-reqs   # pip install -r requirements_test.txt

# After requirements changes
pip install -r requirements.txt -e .
pip install -r requirements_test.txt
```

---

## Make targets (configbp-ai services — identical across all three)

| Target | What it does |
|--------|-------------|
| `make test` | `pytest tests/ -v` + coverage report + JUnit XML → `test-reports/` |
| `make lint` | `flake8 src/` strict gate + McCabe complexity |
| `make format` | `black 26.3.1` |
| `make sync` | `uv sync --locked --group dev --python python3.13` |

---

## Make targets (cbp-engine)

| Target | What it does |
|--------|-------------|
| `make test` | pytest via `python -m pytest` |
| `make run` | start the service |
| `make install-reqs` | `pip install -r requirements.txt -e .` |
| `make install-test-reqs` | `pip install -r requirements_test.txt` |
| `make clean` | remove build artifacts |

---

## Running a single test

```bash
# configbp-ai services
cd configbp-ai/<service-dir>
uv run pytest tests/path/to/test_file.py::test_function_name -v

# cbp-engine
cd assessment-unified-engine
python -m pytest tests/path/to/test_file.py::test_function_name -v
```

---

## Type checking (mypy)

mypy is **not in the Makefiles** — run it manually:

```bash
# configbp-ai services
cd configbp-ai/agent      && uv run mypy .
cd configbp-ai/mcp_server && uv run mypy .
cd configbp-ai/a2a_server && uv run mypy .

# cbp-engine
cd assessment-unified-engine && python -m mypy src/
```

### mypy error quick-fixes

| Error type | Fix |
|-----------|-----|
| `arg-type` incompatible | Add None guard: `if value is not None:` or use `or "default"` |
| `return-value` missing return | Add explicit `return` or fix the branch |
| `import` module not found | Add stub: `uv add --dev types-<pkg>` |
| `attr-defined` | Fix typo or add `# type: ignore[attr-defined]` with a comment |
| External library / unavoidable | `value  # type: ignore[<code>]` — always add a comment explaining why |

---

## Common failures and recovery

### `uv: command not found`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then reload your shell:
source ~/.zshrc   # or ~/.bash_profile
```

### `uv sync` fails with 401 / "package not found"

Cause: Artifactory credentials not set (required for `a2a_server`).

```bash
export UV_INDEX_CISCO_ARTIFACTORY_USERNAME="<username>"
export UV_INDEX_CISCO_ARTIFACTORY_PASSWORD="<token>"
uv sync --locked --group dev --python python3.13
```

### uv.lock conflict / resolution failure

```bash
uv lock           # regenerate the lock file
uv sync --locked --group dev --python python3.13
```

### flake8 E501 — line too long

black auto-fixes line length. Run `make format` first, then re-run `make lint`.

### flake8 F401 — unused import

Remove the import. If it's needed at runtime for side effects, add:
```python
import module  # noqa: F401
```

### black reformatted my file

Expected behaviour — black auto-fixes formatting. Re-stage the file and commit:
```bash
git add <file>
git commit -m "..."
```

### `No module named 'cbp_engine'` (or similar)

```bash
# In a pip project — reinstall in editable mode
pip install -e .

# In a uv project — re-sync
uv sync --locked --group dev --python python3.13
```

### Tests fail with import errors after adding a new package

The lock file may not have been regenerated. Run:
```bash
uv lock && uv sync --locked --group dev --python python3.13
```

---

## Pre-commit (runs black + flake8 + mypy on commit)

```bash
# Install hooks once
uv tool install pre-commit && pre-commit install

# Run all hooks manually
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

---

## When to update this skill

- When a new service is added to configbp-ai
- When cbp-engine switches from pip to uv (or vice versa)
- When Makefile targets change
- When Python version requirements change
- When mypy or flake8 config changes (`pyproject.toml` / `.flake8`)
- When Artifactory setup process changes
