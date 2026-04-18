from __future__ import annotations

import logging
from dataclasses import dataclass

from prometheus_client import Counter, Gauge, start_http_server

logger = logging.getLogger("benchmark_metrics")


@dataclass
class BenchmarkResult:
    task_count: int
    workload_type: str
    enqueue_time: float
    dequeue_time: float
    success_count: int
    failure_count: int
    invalid_count: int
    total_time: float = 0.0

    def __post_init__(self) -> None:
        self.total_time = self.enqueue_time + self.dequeue_time

    @property
    def throughput(self) -> float:
        if self.total_time > 0:
            return self.task_count / self.total_time
        return 0.0


class MetricsCollector:
    def __init__(self, enable_prometheus: bool = True, port: int = 9090) -> None:
        self.enable_prometheus = enable_prometheus
        self.port = port
        self.results: list[BenchmarkResult] = []

        if self.enable_prometheus:
            self._setup_prometheus_metrics()

    def _setup_prometheus_metrics(self) -> None:
        self.enqueue_duration = Gauge(
            "benchmark_enqueue_duration_seconds",
            "Time to enqueue all tasks in a batch",
            ["workload_type", "target", "batch_size"],
        )
        self.dequeue_duration = Gauge(
            "benchmark_dequeue_duration_seconds",
            "Time to retrieve all results in a batch",
            ["workload_type", "target", "batch_size"],
        )
        self.task_success_total = Counter(
            "benchmark_task_success_total",
            "Total successful tasks",
            ["workload_type", "target"],
        )
        self.task_failure_total = Counter(
            "benchmark_task_failure_total",
            "Total failed tasks",
            ["workload_type", "target"],
        )
        self.task_invalid_total = Counter(
            "benchmark_task_invalid_total",
            "Total invalid results",
            ["workload_type", "target"],
        )
        self.throughput = Gauge(
            "benchmark_throughput_tasks_per_second",
            "Tasks processed per second",
            ["workload_type", "target", "batch_size"],
        )
        self.benchmark_run_total = Counter(
            "benchmark_run_total",
            "Total benchmark runs",
            ["workload_type", "target", "status"],
        )

    def start_prometheus_server(self) -> None:
        if self.enable_prometheus:
            try:
                start_http_server(self.port)
                logger.info(f"Prometheus metrics server started on port {self.port}")
            except OSError as e:
                logger.warning(f"Failed to start Prometheus server: {e}")

    def record_result(
        self,
        result: BenchmarkResult,
        target: str,
    ) -> None:
        self.results.append(result)

        if self.enable_prometheus:
            labels = {
                "workload_type": result.workload_type,
                "target": target,
            }
            batch_labels = {
                **labels,
                "batch_size": str(result.task_count),
            }

            self.enqueue_duration.labels(**batch_labels).set(result.enqueue_time)
            self.dequeue_duration.labels(**batch_labels).set(result.dequeue_time)
            self.task_success_total.labels(**labels).inc(result.success_count)
            self.task_failure_total.labels(**labels).inc(result.failure_count)
            self.task_invalid_total.labels(**labels).inc(result.invalid_count)
            self.throughput.labels(**batch_labels).set(result.throughput)
            self.benchmark_run_total.labels(
                **labels,
                status="success" if result.failure_count == 0 else "partial",
            ).inc()

    def log_results(self, target: str) -> None:
        logger.info(f"=============== {target.upper()} RESULTS ===============")
        for result in self.results:
            logger.info(
                f"workload: {result.workload_type}, tasks: {result.task_count:>6}, "
                f"enqueue: {result.enqueue_time:>8.3f}s, "
                f"dequeue: {result.dequeue_time:>8.3f}s, "
                f"throughput: {result.throughput:>8.2f} tasks/s, "
                f"success: {result.success_count}, failed: {result.failure_count}, "
                f"invalid: {result.invalid_count}"
            )
        logger.info("======================================================")
