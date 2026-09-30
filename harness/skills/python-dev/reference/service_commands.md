# Service Commands Cheat-Sheet

Copy-paste reference for every Python service in the CIQ monorepo.

---

## configbp-ai — agent

```bash
cd configbp-ai/agent

# Sync deps
uv sync --locked --group dev --python python3.13

# Format → lint → type check → test
make format
make lint
uv run mypy .
make test

# Run tests only
uv run pytest tests/ -v

# Single test
uv run pytest tests/path/to/test_file.py::test_name -v

# Start service
uv run uvicorn api.server:app --host 0.0.0.0 --port 8081

# Health check
curl http://localhost:8081/health
```

---

## configbp-ai — mcp_server

```bash
cd configbp-ai/mcp_server

# Sync deps
uv sync --locked --group dev --python python3.13

# Format → lint → type check → test
make format
make lint
uv run mypy .
make test

# Run tests only
uv run pytest tests/ -v

# Start service (must start FIRST before agent)
uv run python server.py

# Health check
curl http://localhost:8080/health
```

---

## configbp-ai — a2a_server

```bash
cd configbp-ai/a2a_server

# Sync deps (requires Artifactory credentials)
export UV_INDEX_CISCO_ARTIFACTORY_USERNAME="<username>"
export UV_INDEX_CISCO_ARTIFACTORY_PASSWORD="<token>"
uv sync --locked --group dev --python python3.13

# Format → lint → type check → test
make format
make lint
uv run mypy .
make test

# Run tests only
uv run pytest tests/ -v

# Start service (start after agent)
uv run python server.py

# Health check
curl http://localhost:9000/health
```

---

## configbp-ai — all services (run_all_tests)

```bash
cd configbp-ai
./scripts/run_all_tests.sh
```

---

## configbp-ai — Chainlit UI

```bash
cd configbp-ai
./scripts/start_agent_ui.sh
# Opens http://localhost:8001
# MCP logs → logs/mcp_server.log
```

---

## assessment-unified-engine (cbp-engine)

```bash
cd assessment-unified-engine

# Initial setup
python -m venv venv && source venv/bin/activate
make install-reqs         # pip install -r requirements.txt -e .
make install-test-reqs    # pip install -r requirements_test.txt

# Format → lint → type check → test
black src/
flake8 src/
python -m mypy src/
make test

# Run tests only
make test

# Single test
python -m pytest tests/path/to/test_file.py::test_name -v

# Start service
make run
```

---

## All services — make targets reference

| Target | uv services | cbp-engine |
|--------|------------|-----------|
| `make format` | `black 26.3.1` | ✗ (run `black src/` manually) |
| `make lint` | `flake8` strict + complexity | ✗ (run `flake8 src/` manually) |
| `make test` | pytest + coverage + JUnit XML | pytest |
| `make sync` | `uv sync --locked --group dev` | ✗ |
| `make run` | ✗ | starts the service |
| `make install-reqs` | ✗ | `pip install -r requirements.txt -e .` |
| `make install-test-reqs` | ✗ | `pip install -r requirements_test.txt` |
| `make clean` | ✗ | remove build artifacts |

---

## Pre-commit (all repos)

```bash
# Install once
uv tool install pre-commit && pre-commit install

# Run all hooks manually
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

---

*Last updated: 2026-06-05 — initial version*
