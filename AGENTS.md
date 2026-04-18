# AGENTS.md - Chicory Development Guide

Chicory is a lightweight, async-native job queue for Python (3.11–3.14) with Redis, RabbitMQ, and database backends.

---

## Commands

```bash
make init              # uv sync --dev --all-extras
make lint              # ruff + ty (both)
make ruff              # ruff check --fix
make ty                # ty check (Astral's type checker, not mypy/pyright)

make test              # lint + pytest -vv  (needs Docker services)
make test-fast         # lint + pytest -m "not slow and not integration"
make test-slow         # lint + pytest -n auto -m "slow"
make test-unit         # lint + pytest -n auto -m "not integration"  (includes slow tests)
make test-integration  # lint + pytest -m "integration"

make up                # docker compose up -d --build
make down              # docker compose down -v  ⚠️ -v removes all volumes (destructive)
```

**Every `make test*` target runs lint first.** To skip lint, call pytest directly:

```bash
uv run pytest tests/unit/test_task.py -vv
uv run pytest tests/unit/test_task.py::TestTaskDelay::test_delay_success -vv
```

Coverage runs on every `pytest` invocation (`--cov` is in `addopts`). Add `--no-cov` to suppress it.

---

## Testing Quirks

### asyncio — strict mode
`asyncio_mode = "strict"` is set. **Every `async def test_*` must have `@pytest.mark.asyncio`.**
Omitting it causes the coroutine to be collected but not awaited (silent pass or confusing error).

### Markers
`--strict-markers` is enabled. Only `slow` and `integration` are registered. Any other marker causes a collection failure.

### Integration test services (Docker)
Integration tests require all three services running:
- Redis — `redis://localhost:6379` (db 0 = broker, db 1 = backend)
- RabbitMQ — `amqp://guest:guest@localhost:5672//`
- PostgreSQL — `postgresql+asyncpg://chicory:chicory@localhost:5432/chicory`

### Integration fixture parameterization
`chicory_app` (in `tests/conftest.py`) is parameterized across 4 broker/backend combinations:
`redis-redis`, `rabbitmq-postgres`, `redis-postgres`, `rabbitmq-redis`.
Each integration test runs **4 times**. Postgres schema is created by the fixture (`Base.metadata.create_all`), not by a migration script.

### `test-unit` label is misleading
`make test-unit` uses `-m "not integration"` — it includes `slow` tests. Only `make test-fast` excludes both slow and integration.

---

## Non-Obvious Architecture

### Optional dependency guards
`src/chicory/__init__.py` wraps broker/backend imports in `try/except ImportError`.
`__init__.py` has `F401` ignored in ruff so these conditional re-exports don't trigger lint errors.
`tests/unit/test_optional_imports.py` explicitly tests these guards — don't break them.

### `TaskMessage` serializes with pickle (not JSON)
`TaskMessage.dumps()` / `TaskMessage.loads()` use pickle. Never consume from untrusted brokers.

### Key locations that aren't obvious from the directory tree
- `DEFAULT_QUEUE` and `TaskEnvelope` type → `broker/base.py`
- SQLAlchemy `Base` metadata → `backend/models.py`
- CLI entrypoint → `cli/cli.py` (typer app, invoked as `chicory worker <module:broker>`)
- Worker uses `ThreadPoolExecutor` for sync task functions

### uv workspace
`benchmarks/` is a uv workspace member with its own `pyproject.toml`. Run benchmark commands from within `benchmarks/` or via `benchmarks/Makefile`.

### Build backend
`uv_build>=0.9.13,<0.10.0` — not setuptools or hatch.

---

## Ruff / Style Gotchas

- `target-version = "py314"` — ruff enforces Python 3.14 compatibility
- `TD` rule is enabled: TODOs must use `# TODO(author): description` format
- `NPY` rule is enabled (numpy conventions) even though numpy is not a dependency
- `docstring-code-format = true` with `docstring-code-line-length = "dynamic"`
- `from __future__ import annotations` required at the top of every source file
- `src/chicory/logging.py` is omitted from coverage measurement

---

## CI Summary

| Workflow | Trigger | Services | Command |
|---|---|---|---|
| `pr-unit-tests.yml` | PR | none | `make test-unit` |
| `merge-gate.yml` | merge queue | Redis, Postgres 17, RabbitMQ 3 | `make test` |
| `post-merge-coverage.yml` | push to `main` | Docker via `make up` | `make test` + Codecov |

PRs only run unit tests. Full integration tests run at merge gate. Coverage XML (`coverage.xml`) is uploaded to Codecov on main merges.
