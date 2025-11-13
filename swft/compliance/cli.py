"""
Typer-based CLI entrypoint for the compliance authoring engine.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import Config, load_config
from .store import MigrationRunner, get_connection
from .importers.oscal.catalog_importer import CatalogImporter
from .importers.oscal.profile_importer import ProfileImporter
from .oscal.sources import NistSp80053Source, OscalDownloadError
from .projects import ProjectsManager
from .controls import ControlService
from .mapping import ensure_implemented_requirement
from .utils.parsing import parse_csv_list, parse_bool
from .evidence.sbom_cyclonedx import SbomIngestor
from .evidence.trivy import TrivyIngestor
from .evidence.signatures import SignatureIngestor
from .importers.azure.policy_definition_importer import PolicyDefinitionImporter
from .importers.azure.policy_state_importer import PolicyStateImporter

console = Console()
app = typer.Typer(help="SWFT Compliance Authoring Engine CLI", no_args_is_help=True)
config_app = typer.Typer(help="Inspect resolved configuration.")
store_app = typer.Typer(help="Database and migration utilities.")
oscal_app = typer.Typer(help="Import OSCAL catalogs and baselines.")
project_app = typer.Typer(help="Manage project boundaries and metadata.")
control_app = typer.Typer(help="Inspect and set control parameters.")
evidence_app = typer.Typer(help="Manage evidence artifacts.")
evidence_add_app = typer.Typer(help="Add evidence from pipeline outputs.")
evidence_app.add_typer(evidence_add_app, name="add")
policy_app = typer.Typer(help="Import Azure Policy definitions and state snapshots.")


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


@oscal_app.command("sync-catalog")
def oscal_sync_catalog(
    ctx: typer.Context,
    catalog: Path = typer.Option(..., "--catalog", help="Path to the OSCAL catalog JSON (e.g., SP 800-53)."),
    baseline: Path = typer.Option(..., "--baseline", help="Path to the FedRAMP OSCAL profile JSON."),
    name: str = typer.Option(..., "--name", "-n", help="Baseline name identifier (e.g., fedramp-high)."),
    catalog_name: str = typer.Option("sp800-53-r5.2.0", "--catalog-name", help="Version label for the catalog entry."),
) -> None:
    """Import catalog + baseline into the store with pinned versions."""
    config = _get_config(ctx)
    catalog_importer = CatalogImporter(config)
    baseline_importer = ProfileImporter(config)
    cat_result = catalog_importer.ingest(catalog_path=catalog, name=catalog_name)
    base_result = baseline_importer.ingest(profile_path=baseline, profile_name=name)
    console.print(
        f"[green]Catalog '{catalog_name}' pinned ({cat_result.control_count} controls). File: {cat_result.pinned_path}[/]"
    )
    console.print(
        f"[green]Baseline '{name}' imported with {base_result.control_count} controls. File: {base_result.pinned_path}[/]"
    )


@oscal_app.command("sync-nist-sp80053")
def oscal_sync_nist_sp80053(
    ctx: typer.Context,
    baseline_level: str = typer.Option(
        "moderate",
        "--baseline",
        "-b",
        help="Baseline profile to download (low, moderate, high, privacy).",
    ),
    version: str = typer.Option("v1.3.0", "--version", help="Git tag/branch from usnistgov/oscal-content."),
    file_format: str = typer.Option("json", "--format", help="File format folder to download (json, yaml, xml)."),
    catalog_name: str = typer.Option("sp800-53-r5.2.0", "--catalog-name", help="Stored label for the catalog version."),
    baseline_name: str | None = typer.Option(None, "--baseline-name", help="Stored label for the baseline version."),
) -> None:
    """
    Download the SP 800-53 Rev5 catalog/baseline from NIST and import them.
    """

    config = _get_config(ctx)
    download_dir = config.paths.outputs / "downloads" / "nist-sp800-53" / version / file_format
    source_kwargs = {}
    env_base = os.environ.get("SWFT_OSCAL_BASE_URL")
    if env_base:
        source_kwargs["base_url_template"] = env_base
    source = NistSp80053Source(version=version, file_format=file_format, **source_kwargs)
    console.print(f"[cyan]Downloading catalog from {source.catalog_url()}[/]")
    try:
        catalog_path = source.download_catalog(download_dir)
        profile_path = source.download_baseline(baseline_level, download_dir)
    except (OscalDownloadError, ValueError) as exc:
        raise typer.BadParameter(str(exc))

    catalog_importer = CatalogImporter(config)
    baseline_importer = ProfileImporter(config)
    cat_result = catalog_importer.ingest(catalog_path=catalog_path, name=catalog_name)
    profile_label = baseline_name or f"sp800-53-{baseline_level.lower()}"
    base_result = baseline_importer.ingest(profile_path=profile_path, profile_name=profile_label)
    console.print(f"[green]Catalog '{catalog_name}' pinned ({cat_result.control_count} controls). File: {cat_result.pinned_path}[/]")
    console.print(
        f"[green]Baseline '{profile_label}' imported with {base_result.control_count} controls. File: {base_result.pinned_path}[/]"
    )


@project_app.command("init")
def project_init(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Project identifier (unique)."),
    services: str = typer.Option("", "--services", help="Comma-separated list of Azure services used."),
    regions: str = typer.Option("", "--regions", help="Comma-separated list of Azure regions."),
    boundary_file: Path | None = typer.Option(
        None,
        "--boundary-file",
        exists=True,
        readable=True,
        help="Path to a markdown/text file describing the system boundary.",
    ),
) -> None:
    """Create a project boundary definition."""
    config = _get_config(ctx)
    mgr = ProjectsManager(config)
    boundary_text = boundary_file.read_text() if boundary_file else None
    try:
        record = mgr.create_project(
            key=name,
            services=parse_csv_list(services),
            regions=parse_csv_list(regions),
            boundary_description=boundary_text,
        )
    except ValueError as exc:  # pragma: no cover
        raise typer.BadParameter(str(exc))
    console.print(f"[green]Project '{record.key}' created (id={record.id}).[/]")


@project_app.command("list")
def project_list(ctx: typer.Context) -> None:
    """List all configured projects."""
    config = _get_config(ctx)
    mgr = ProjectsManager(config)
    records = mgr.list_projects()
    if not records:
        console.print("[yellow]No projects found. Use 'swft project init' to create one.[/]")
        return
    table = Table(title="Projects", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Services")
    table.add_column("Regions")
    table.add_column("Boundary (first line)")
    for record in records:
        boundary_line = (record.boundary_description or "").splitlines()[0:1]
        table.add_row(
            record.key,
            ", ".join(record.services) or "—",
            ", ".join(record.regions) or "—",
            boundary_line[0] if boundary_line else "—",
        )
    console.print(table)


@project_app.command("show")
def project_show(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Project identifier."),
) -> None:
    """Show details for a single project."""
    config = _get_config(ctx)
    mgr = ProjectsManager(config)
    try:
        record = mgr.get_project(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    table = Table(title=f"Project: {record.key}", show_header=False)
    table.add_row("ID", str(record.id))
    table.add_row("Services", ", ".join(record.services) or "—")
    table.add_row("Regions", ", ".join(record.regions) or "—")
    table.add_row("Boundary", record.boundary_description or "—")
    console.print(table)


@control_app.command("list-params")
def control_list_params(
    ctx: typer.Context,
    control: str = typer.Option(..., "--control", "-c", help="Control identifier (e.g., AC-2)."),
    project: str | None = typer.Option(None, "--project", "-p", help="Optional project to show current values."),
) -> None:
    """List parameters for a control, optionally including project values."""
    config = _get_config(ctx)
    param_service = ControlService(config)
    project_id = None
    if project:
        try:
            project_id = ProjectsManager(config).get_project(project).id
        except ValueError as exc:
            raise typer.BadParameter(str(exc))
    params = param_service.list_parameters(control, project_id=project_id)
    if not params:
        console.print("[yellow]This control has no parameters.[/]")
        return
    table = Table(title=f"Parameters: {control}", show_header=True, header_style="bold magenta")
    table.add_column("Param ID", style="cyan")
    table.add_column("Label")
    table.add_column("Allowed Values")
    table.add_column("Current Value")
    for param in params:
        table.add_row(
            param.param_id,
            param.label or "—",
            ", ".join(param.values) or "—",
            param.current_value or "—",
        )
    console.print(table)


@control_app.command("set-param")
def control_set_param(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project", "-p", help="Project identifier."),
    control: str = typer.Option(..., "--control", "-c", help="Control identifier (e.g., AC-2)."),
    param: str = typer.Option(..., "--param", help="Parameter identifier (e.g., ac-2_prm_1)."),
    value: str = typer.Option(..., "--value", help="Parameter value to store for this project."),
) -> None:
    """Set a control parameter value for a specific project."""
    config = _get_config(ctx)
    projects = ProjectsManager(config)
    try:
        record = projects.get_project(project)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    try:
        ControlService(config).ensure_parameter_exists(control, param)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    with get_connection(config) as conn:
        conn.execute("SET search_path TO swft, public")
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO parameter_values (project_fk, control_id, param_id, value)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (project_fk, control_id, param_id)
                DO UPDATE SET value = excluded.value
                """,
                (record.id, control, param, value),
            )
            ensure_implemented_requirement(conn, project_id=record.id, control_id=control)
        conn.commit()
    console.print(f"[green]Parameter {param} for control {control} set to '{value}' (project {project}).[/]")


@evidence_add_app.command("sbom")
def evidence_add_sbom(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project", "-p", help="Project identifier."),
    run_id: str = typer.Option(..., "--run-id", "-r", help="Run identifier (matches CI run id or commit)."),
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="CycloneDX SBOM JSON file."),
) -> None:
    """Ingest a CycloneDX SBOM."""
    config = _get_config(ctx)
    mgr = ProjectsManager(config)
    try:
        project_record = mgr.get_project(project)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    ingestor = SbomIngestor(config)
    evidence, count = ingestor.ingest(project=project_record, run_id=run_id, sbom_path=file)
    console.print(
        f"[green]Stored SBOM with {count} components for run {run_id}. Evidence file: {evidence.file_path}[/]"
    )


@evidence_add_app.command("trivy")
def evidence_add_trivy(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project", "-p", help="Project identifier."),
    run_id: str = typer.Option(..., "--run-id", "-r", help="Run identifier."),
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="Trivy JSON report."),
    artifact: str = typer.Option(
        "",
        "--artifact",
        "-a",
        help="Optional artifact hint if the report is missing target metadata.",
    ),
) -> None:
    """Ingest a Trivy report and persist vulnerability findings."""
    config = _get_config(ctx)
    mgr = ProjectsManager(config)
    try:
        project_record = mgr.get_project(project)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    ingestor = TrivyIngestor(config)
    evidence, count = ingestor.ingest(
        project=project_record,
        run_id=run_id,
        trivy_path=file,
        artifact_hint=artifact or None,
    )
    console.print(
        f"[green]Stored Trivy report with {count} finding(s) for run {run_id}. Evidence file: {evidence.file_path}[/]"
    )


@evidence_add_app.command("signature")
def evidence_add_signature(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project", "-p", help="Project identifier."),
    run_id: str = typer.Option(..., "--run-id", "-r", help="Run identifier."),
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="cosign verify --json output."),
    digest: str = typer.Option(..., "--digest", help="Image digest (e.g., sha256:abcd)."),
    verified: str = typer.Option(..., "--verified", help="true/false result from cosign verify."),
) -> None:
    """Record cosign verification output."""
    config = _get_config(ctx)
    mgr = ProjectsManager(config)
    try:
        project_record = mgr.get_project(project)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    try:
        verified_bool = parse_bool(verified)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    ingestor = SignatureIngestor(config)
    evidence = ingestor.ingest(
        project=project_record,
        run_id=run_id,
        signature_path=file,
        digest=digest,
        verified=verified_bool,
    )
    status = "verified" if verified_bool else "NOT verified"
    console.print(
        f"[green]Recorded signature evidence for run {run_id} ({status}). Evidence file: {evidence.file_path}[/]"
    )


@policy_app.command("import")
def policy_import(
    ctx: typer.Context,
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="Azure Policy initiative JSON file."),
    name: str = typer.Option(..., "--name", "-n", help="Initiative identifier (e.g., nist-sp-800-53-r5)."),
    scope: str = typer.Option("commercial", "--scope", help="Scope label: 'commercial' or 'gov'."),
) -> None:
    """Import Azure Policy initiative definitions and control mappings."""
    config = _get_config(ctx)
    importer = PolicyDefinitionImporter(config)
    try:
        result = importer.ingest(file_path=file, name=name, scope=scope)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    console.print(
        f"[green]Imported initiative '{name}' ({result.policy_count} policies, {result.mapping_count} control links).[/]"
    )
    console.print(f"Pinned file: {result.pinned_path}")


@policy_app.command("import-states")
def policy_import_states(
    ctx: typer.Context,
    file: Path = typer.Option(..., "--file", "-f", exists=True, readable=True, help="Policy state snapshot JSON."),
    initiative: str = typer.Option(..., "--initiative", "-i", help="Initiative identifier to associate states with."),
    scope: str = typer.Option("commercial", "--scope", help="Scope label: 'commercial' or 'gov'."),
) -> None:
    """Import policy evaluation states to attach telemetry to controls."""
    config = _get_config(ctx)
    importer = PolicyStateImporter(config)
    try:
        result = importer.ingest(file_path=file, initiative_name=initiative, scope=scope)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    console.print(
        f"[green]Processed {result.rows_processed} state entries; inserted {result.rows_inserted} telemetry rows.[/]"
    )


app.add_typer(config_app, name="config")
app.add_typer(store_app, name="store")
app.add_typer(oscal_app, name="oscal")
app.add_typer(project_app, name="project")
app.add_typer(control_app, name="control")
app.add_typer(evidence_app, name="evidence")
app.add_typer(policy_app, name="policy")


if __name__ == "__main__":
    app()
