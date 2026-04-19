# Benchmarks

Chicory ships an internal benchmark suite in the `benchmarks/` directory that provides
an apple-to-apple comparison of **Chicory** vs **TaskIQ**, both using Redis as broker
and result backend.

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ with [uv](https://docs.astral.sh/uv/)

The benchmark workspace is
a [uv workspace member](https://docs.astral.sh/uv/concepts/workspaces/)
with its own `pyproject.toml`. All commands should be run from the `benchmarks/`
directory (or via `benchmarks/Makefile`).

## Quick Start

```bash
# From the repository root:
cd benchmarks

# 1. Install benchmark dependencies
uv sync --dev --all-extras

# 2. Start Redis, Prometheus, and Grafana
make up

# 3. Terminal 1 — start a worker (pick one)
make chicory-worker    # 4 processes × 32 concurrency = 128 concurrent
make taskiq-worker     # 4 processes × 32 max-async-tasks = 128 concurrent

# 4. Terminal 2 — run benchmarks
make chicory-run-all   # all workloads
make taskiq-run-all

# 5. View results
#    Console — printed at end of each run
#    Grafana — http://localhost:3000 (dashboard: "Chicory Benchmarks")
#    Prometheus — http://localhost:9100
```

## What's Measured

Each benchmark iterates over batch sizes
`[8, 16, 32, 64, 128, 256, 1024, 2048, 4096, 8192, 16384]` and records:

| Metric                          | Description                                           |
|---------------------------------|-------------------------------------------------------|
| **Enqueue duration**            | Wall time to `gather()` all `delay()` / `kiq()` calls |
| **Dequeue duration**            | Wall time to `gather()` all result retrievals         |
| **Throughput**                  | `batch_size / (enqueue + dequeue)`                    |
| **Success / Failure / Invalid** | Per-batch result classification                       |

Redis is flushed (both db 0 and db 1) between batches to prevent data leakage.

## Workload Types

| Workload    | Task body                                 | Purpose                                  |
|-------------|-------------------------------------------|------------------------------------------|
| `increment` | `return value + 1`                        | Baseline — pure enqueue/dequeue overhead |
| `cpu_bound` | 10k iterations of `(x * 31 + 17) % 1e9+7` | CPU-bound worker load                    |
| `io_bound`  | `asyncio.sleep(0.01)`                     | I/O-bound / concurrency pressure         |

Run individual workloads:

```bash
make chicory-run-increment
make chicory-run-cpu
make chicory-run-io
make chicory-run-all

# Same targets exist for taskiq:
make taskiq-run-all
```

## Fairness Controls

Both frameworks try as much as possible to run under equivalent conditions:

| Setting                | Chicory               | TaskIQ                |
|------------------------|-----------------------|-----------------------|
| Workers (processes)    | 4                     | 4                     |
| Concurrency per worker | 32                    | 32                    |
| Broker                 | Redis Streams (db 0)  | Redis Streams (db 0)  |
| Result backend         | Redis (db 1)          | Redis (db 1)          |
| Validation overhead    | `ValidationMode.NONE` | N/A (none by default) |
| Connection pool        | Default               | Default               |

## Reading the Results

### Console output

At the end of each run, a summary table is printed to the console showing
per-batch-size rows with enqueue duration, dequeue duration, throughput
(tasks/sec), and success/failure/invalid counts.

**What to look for:**

- **Throughput scaling**: throughput should increase with batch size up to a
  plateau. If it drops, the bottleneck is usually Redis or result polling.
- **Enqueue vs dequeue split**: enqueue is typically fast; if dequeue dominates,
  the result backend or polling interval may be the bottleneck.
- **Failures / invalid**: should be zero. Non-zero values indicate bugs or
  resource exhaustion.

### Grafana dashboard

The auto-provisioned Grafana dashboard (at `http://localhost:3000`) has 9 panels:

1. Enqueue duration per batch
2. Dequeue duration per batch
3. Throughput (tasks/sec)
4. Success count
5. Failure count
6. Invalid count
7. Redis memory usage
8. Redis ops/sec
9. Redis connected clients

Use the template variables at the top to filter by **target** (`chicory`,
`taskiq`, or both) and **workload_type** (`increment`, `cpu_bound`, `io_bound`, or all).

## Monitoring Stack

| Service        | Internal port | External port |
|----------------|---------------|---------------|
| Redis          | 6379          | 6379          |
| Redis Exporter | 9121          | —             |
| Prometheus     | 9090          | **9100**      |
| Grafana        | 3000          | 3000          |

Prometheus is mapped to **9100** externally to avoid conflict with Chicory's
metrics endpoint on 9090.

## Cleanup

```bash
make down    # Stop all containers and remove volumes
```

## Adding New Benchmarks

1. Create `benchmarks/broker_redis/bench_<name>.py` following the pattern in
   existing bench files.
2. Define tasks, `_WORKLOAD_TASKS` mapping, `_flush_redis()`, `_run_batch()`.
3. Use `MetricsCollector.record_result(result, "<name>")` for Prometheus export.
4. Add `make <name>-worker` and `make <name>-run-*` targets to the Makefile.
5. Add a Prometheus scrape target in `monitor/prometheus.yml`.
6. Update the Grafana dashboard `target` template variable.

For full implementation details, see `benchmarks/README.md` in the repository.
