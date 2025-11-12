"""
Typer-based CLI entrypoint for the compliance authoring engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import Config, load_config
from .store import MigrationRunner, get_connection

console = Console()
app = typer.Typer(help="SWFT Compliance Authoring Engine CLI", no_args_is_help=True)
config_app = typer.Typer(help="Inspect resolved configuration.")
store_app = typer.Typer(help="Database and migration utilities.")


def _get_config(ctx: typer.Context) -> Config:
    if ctx.obj is None or "config" not in ctx.obj:
        raise typer.BadParameter("Configuration was not initialized. Ensure the CLI callback executed.")
    return ctx.obj["config"]


@app.callback()
def main(
    ctx: typer.Context,
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Optional path to swft.toml. Defaults to ./swft.toml if present.",
    ),
) -> None:
    config = load_config(config_file)
    config.paths.ensure()
    ctx.obj = {"config": config}


@config_app.command("show")
def config_show(ctx: typer.Context) -> None:
    """Print the resolved configuration values."""
    config = _get_config(ctx)
    table = Table(title="SWFT Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Key", style="cyan")
    table.add_column("Value", overflow="fold")
    table.add_row("DB Host", config.db.host)
    table.add_row("DB Port", str(config.db.port))
    table.add_row("DB Name", config.db.name)
    table.add_row("DB User", config.db.user)
    table.add_row("DB Auth Mode", config.db.auth_mode)
    table.add_row("DB AAD Scope", config.db.aad_scope)
    table.add_row("Store Dir", str(config.paths.store))
    table.add_row("Pinned Dir", str(config.paths.pinned))
    table.add_row("Outputs Dir", str(config.paths.outputs))
    console.print(table)


@store_app.command("migrate")
def store_migrate(ctx: typer.Context) -> None:
    """Apply any pending SQL migrations."""
    config = _get_config(ctx)
    runner = MigrationRunner(config, console=console)
    applied = runner.apply()
    if not applied:
        console.print("[green]All migrations already applied.[/]")
    else:
        console.print(f"[green]Applied {len(applied)} migration(s).[/]")


@store_app.command("doctor")
def store_doctor(ctx: typer.Context) -> None:
    """Verify database connectivity and migration status."""
    config = _get_config(ctx)
    with console.status("Connecting to database"):
        with get_connection(config) as conn:
            conn.execute("SELECT 1")
    console.print("[green]Database connection successful.[/]")
    runner = MigrationRunner(config, console=console)
    migrations, applied = runner.status()
    table = Table(title="Migration Status", show_header=True, header_style="bold magenta")
    table.add_column("Filename", style="cyan")
    table.add_column("Checksum")
    table.add_column("Applied?", justify="center")
    for migration in migrations:
        table.add_row(
            migration.filename,
            migration.checksum[:10] + "…",
            "✅" if migration.filename in applied else "❌",
        )
    console.print(table)


app.add_typer(config_app, name="config")
app.add_typer(store_app, name="store")


if __name__ == "__main__":
    app()

