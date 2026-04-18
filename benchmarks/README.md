# Benchmarks

Apple-to-apple comparison of **Chicory** vs **TaskIQ**, both using Redis as broker and
result backend.

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ with `uv`

## Quick start

```bash
# 1. Install benchmark deps
uv sync --dev --all-extras

# 2. Start Redis, Prometheus, Grafana
make up

# 3. Terminal 1 — start a worker (pick one)
make chicory-worker    # 4 processes × 32 concurrency = 128 concurrent
make taskiq-worker     # 4 processes × 32 max-async-tasks = 128 concurrent

# 4. Terminal 2 — run benchmark
make chicory-run-all
make taskiq-run-all

# 5. View results
#    Console — printed at end of run
#    Grafana — http://localhost:3000 (dashboard: "Chicory Benchmarks")
#    Prometheus — http://localhost:9100
```

## What's measured

Each benchmark iterates over batch sizes
`[8, 16, 32, 64, 128, 256, 1024, 2048, 4096, 8192, 16384]` and records:

| Metric                      | Description                                         |
|-----------------------------|-----------------------------------------------------|
| **Enqueue duration**        | Wall time to `gather()` all `delay()`/`kiq()` calls |
| **Dequeue duration**        | Wall time to `gather()` all result retrievals       |
| **Throughput**              | `batch_size / (enqueue + dequeue)`                  |
| **Success/Failure/Invalid** | Per-batch result classification                     |

Redis is flushed (both db 0 and db 1) between batches to prevent data leakage.

## Workload types

| Workload    | Task body                                 | Purpose                                  |
|-------------|-------------------------------------------|------------------------------------------|
| `increment` | `return value + 1`                        | Baseline — pure enqueue/dequeue overhead |
| `cpu_bound` | 10k iterations of `(x * 31 + 17) % 1e9+7` | CPU-bound worker load                    |
| `io_bound`  | `asyncio.sleep(0.01)`                     | I/O-bound / concurrency pressure         |

```bash
make chicory-run-increment   # or cpu, io, all
make taskiq-run-all
```

## Fairness controls

Both frameworks run under equivalent conditions:

| Setting                | Chicory               | TaskIQ                |
|------------------------|-----------------------|-----------------------|
| Workers (processes)    | 4                     | 4                     |
| Concurrency per worker | 32                    | 32                    |
| Broker                 | Redis streams (db 0)  | Redis streams (db 0)  |
| Result backend         | Redis (db 1)          | Redis (db 1)          |
| Validation overhead    | `ValidationMode.NONE` | N/A (none by default) |
| Connection pool        | Default               | Default               |

## Monitoring

### Services (via `docker compose`)

| Service        | Internal port | External port |
|----------------|---------------|---------------|
| Redis          | 6379          | 6379          |
| Redis Exporter | 9121          | —             |
| Prometheus     | 9090          | **9100**      |
| Grafana        | 3000          | 3000          |

Prometheus is on **9100** externally to avoid conflict with Chicory's metrics endpoint
on 9090.

### Prometheus targets

| Job                 | Target                      | Notes                 |
|---------------------|-----------------------------|-----------------------|
| `redis_exporter`    | `redis-exporter:9121`       | Inside docker network |
| `chicory_benchmark` | `host.docker.internal:9090` | Bench script on host  |
| `taskiq_benchmark`  | `host.docker.internal:9091` | Bench script on host  |

### Grafana dashboard

Auto-provisioned at startup. Template variables:

- **target**: `chicory`, `taskiq`, or both
- **workload_type**: `increment`, `cpu_bound`, `io_bound`, or all

9 panels: enqueue/dequeue duration, throughput, success/failure/invalid counts, Redis
memory, Redis ops/sec, Redis connected clients.

## Architecture

```
benchmarks/
├── broker_redis/
│   ├── bench_chicory.py      # Chicory benchmark script + task definitions
│   └── bench_taskiq.py       # TaskIQ benchmark script + task definitions
├── framework/
│   ├── __init__.py
│   ├── config.py             # BenchmarkConfig, WorkloadType enum
│   ├── metrics.py            # MetricsCollector, BenchmarkResult, Prometheus gauges/counters
│   ├── runner.py             # BenchmarkRunner (generic, for future use)
│   └── workloads.py          # Task creator functions (for runner.py)
├── monitor/
│   ├── prometheus.yml
│   └── grafana/
│       ├── datasources.yml
│       ├── dashboards.yml
│       └── dashboards/
│           └── benchmarks.json
├── docker-compose.yml
├── Makefile
└── pyproject.toml            # uv workspace member
```

## Adding new benchmarks

1. Create `broker_redis/bench_<name>.py` following the pattern in existing bench files
2. Define tasks, `_WORKLOAD_TASKS` mapping, `_flush_redis()`, `_run_batch()`
3. Use `MetricsCollector.record_result(result, "<name>")` for Prometheus export
4. Add `make <name>-worker` and `make <name>-run-*` targets to `Makefile`
5. Add a Prometheus scrape target in `monitor/prometheus.yml`
6. Update the Grafana dashboard `target` template variable

## Cleanup

```bash
make down          # Stop all containers, remove volumes
```
