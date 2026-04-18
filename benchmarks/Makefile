.PHONY: up down
.PHONY: chicory-worker chicory-run chicory-run-increment chicory-run-cpu chicory-run-io chicory-run-all
.PHONY: taskiq-worker taskiq-run taskiq-run-increment taskiq-run-cpu taskiq-run-io taskiq-run-all

# ── Infrastructure ──────────────────────────────────────────────
up:
	docker compose up -d --build

down:
	docker compose down -v

# ── Chicory ─────────────────────────────────────────────────────
chicory-worker:
	chicory worker --workers 4 --concurrency 32 broker_redis.bench_chicory:app

chicory-run:
	python broker_redis/bench_chicory.py

chicory-run-increment:
	python broker_redis/bench_chicory.py --workload increment

chicory-run-cpu:
	python broker_redis/bench_chicory.py --workload cpu_bound

chicory-run-io:
	python broker_redis/bench_chicory.py --workload io_bound

chicory-run-all:
	python broker_redis/bench_chicory.py --workload all

# ── TaskIQ ──────────────────────────────────────────────────────
taskiq-worker:
	taskiq worker --workers 4 --max-async-tasks 32 broker_redis.bench_taskiq:broker --max-prefetch 32

taskiq-run:
	python broker_redis/bench_taskiq.py

taskiq-run-increment:
	python broker_redis/bench_taskiq.py --workload increment

taskiq-run-cpu:
	python broker_redis/bench_taskiq.py --workload cpu_bound

taskiq-run-io:
	python broker_redis/bench_taskiq.py --workload io_bound

taskiq-run-all:
	python broker_redis/bench_taskiq.py --workload all
