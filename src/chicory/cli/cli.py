import asyncio
import importlib
import importlib.metadata
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import typer

from chicory.app import Chicory
from chicory.worker import Worker

if TYPE_CHECKING:
    from chicory.types import WorkerStats

app = typer.Typer(help="Chicory task queue worker CLI.")


def _import_app(app_path: str) -> Chicory:
    """Import the Chicory app from the given path."""
    # Add current directory to sys.path so we can import user modules
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    if ":" in app_path:
        module_path, app_name = app_path.rsplit(":", 1)
    else:
        module_path = app_path
        app_name = "app"

    module = importlib.import_module(module_path)
    chicory_app = getattr(module, app_name)

    if not isinstance(chicory_app, Chicory):
        raise TypeError(f"The object '{app_name}' is not a Chicory app instance.")

    return chicory_app


@app.command()
def worker(
    app_path: str = typer.Argument(
        ..., help="Path to the Chicory app (e.g., 'myapp.tasks:app')"
    ),
    concurrency: int = typer.Option(
        4, "--concurrency", "-c", help="Number of concurrent workers"
    ),
    queue: str = typer.Option("default", "--queue", "-q", help="Queue to consume from"),
    use_dead_letter_queue: bool = typer.Option(
        False,
        "--dlq/--no-dlq",
        help="Enable or disable Dead Letter Queue handling",
    ),
    heartbeat_interval: float = typer.Option(
        10.0, "--heartbeat-interval", help="Interval in seconds for heartbeat signals"
    ),
    heartbeat_ttl: int = typer.Option(
        30, "--heartbeat-ttl", help="Time-to-live in seconds for heartbeat signals"
    ),
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = typer.Option(
        "INFO", "--log-level", help="Set the logging level (e.g., DEBUG, INFO, WARNING)"
    ),
) -> None:
    """
    Start a Chicory worker.
    """
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = _import_app(app_path)

    worker_instance = Worker(
        app,
        concurrency=concurrency,
        queue=queue,
        use_dead_letter_queue=use_dead_letter_queue,
        heartbeat_interval=heartbeat_interval,
        heartbeat_ttl=heartbeat_ttl,
    )

    typer.echo(f"Starting Chicory worker for {app_path}")
    typer.echo(f"Log Level: {log_level}")
    typer.echo(f"Concurrency: {concurrency}")
    typer.echo(f"Queue: {queue}")
    typer.echo(f"Heartbeat Interval: {heartbeat_interval}s")
    typer.echo(f"Heartbeat TTL: {heartbeat_ttl}s")
    typer.echo(
        f"Dead Letter Queue: {'Enabled' if use_dead_letter_queue else 'Disabled'}"
    )

    asyncio.run(worker_instance.run())


@app.command()
def workers(
    app_path: str = typer.Argument(
        ..., help="Path to the Chicory app (e.g., 'myapp.tasks:app')"
    ),
) -> None:
    """
    List all active workers.
    """

    app = _import_app(app_path)

    async def list_workers():
        if not app.backend:
            typer.echo("No backend configured. Cannot retrieve worker info.")
            return

        await app.connect()

        try:
            workers: list[WorkerStats] = await app.backend.get_active_workers()

            if not workers:
                typer.echo("No active workers found.")
                return

            typer.echo(f"\n{'=' * 80}")
            typer.echo(f"Active Workers: {len(workers)}")
            typer.echo(f"{'=' * 80}\n")

            for w in workers:
                status_icon = "🟢" if w.is_running else "🔴"
                typer.echo(f"{status_icon} Worker: {w.worker_id}")
                typer.echo(f"   Hostname: {w.hostname} (PID: {w.pid})")
                typer.echo(f"   Queue: {w.queue}")
                typer.echo(f"   Uptime: {w.uptime_seconds:.1f}s")
                typer.echo(
                    f"   Tasks: {w.tasks_processed} processed, "
                    f"{w.tasks_failed} failed, {w.active_tasks} active"
                )
                last_heartbeat_str = (
                    w.last_heartbeat.isoformat() if w.last_heartbeat else "N/A"
                )
                typer.echo(f"   Last heartbeat: {last_heartbeat_str}")
                typer.echo()
        finally:
            await app.disconnect()

    asyncio.run(list_workers())


@app.command()
def cleanup(
    app_path: str = typer.Argument(
        ..., help="Path to the Chicory app (e.g., 'myapp.tasks:app')"
    ),
    stale_seconds: int = typer.Option(
        60, help="Remove workers with no heartbeat for this many seconds"
    ),
) -> None:
    """
    Cleanup stale worker records.
    """

    app = _import_app(app_path)

    async def cleanup():
        if not app.backend:
            typer.echo("No backend configured. Cannot clean up workers.")
            return

        await app.connect()
        try:
            removed_count = await app.backend.cleanup_stale_workers(stale_seconds)
            typer.echo(f"Removed {removed_count} stale worker(s).")
        finally:
            await app.disconnect()

    asyncio.run(cleanup())


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show the Chicory version and exit"
    ),
) -> None:
    """
    Chicory task queue CLI.
    """
    if version:
        _version = importlib.metadata.version("chicory")
        typer.echo(f"Chicory version: {_version}")
        raise typer.Exit()

    # If no command was invoked, show help
    if ctx.invoked_subcommand is None and not version:
        typer.echo(ctx.get_help())
        raise typer.Exit()
