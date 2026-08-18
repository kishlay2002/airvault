"""VaultMind Admin CLI

Usage:
    vaultmind collections list
    vaultmind ingest status
    vaultmind audit --user analyst-1
    vaultmind users list
    vaultmind health
"""

import json
import click
from rich.console import Console
from rich.table import Table

from vaultmind.client import get_client

console = Console()


@click.group()
def cli():
    """VaultMind — Air-Gapped Document Intelligence Engine CLI"""
    pass


# --- Collections ---
@cli.group()
def collections():
    """Manage document collections."""
    pass


@collections.command("list")
def collections_list():
    """List all collections."""
    with get_client() as client:
        resp = client.get("/api/v1/collections")
        resp.raise_for_status()

    table = Table(title="Collections")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Documents", justify="right")
    table.add_column("Created")

    for c in resp.json():
        table.add_row(
            c["name"],
            c.get("description", ""),
            str(c.get("document_count", 0)),
            c.get("created_at", "")[:19],
        )

    console.print(table)


@collections.command("create")
@click.option("--name", required=True, help="Collection name")
@click.option("--description", default="", help="Collection description")
def collections_create(name: str, description: str):
    """Create a new collection."""
    with get_client() as client:
        resp = client.post("/api/v1/collections", json={"name": name, "description": description})
        resp.raise_for_status()

    console.print(f"[green]Created collection '{name}'[/green]")


@collections.command("delete")
@click.option("--name", required=True, help="Collection name")
@click.confirmation_option(prompt="Are you sure you want to delete this collection?")
def collections_delete(name: str):
    """Delete a collection."""
    with get_client() as client:
        resp = client.delete(f"/api/v1/collections/{name}")
        resp.raise_for_status()

    console.print(f"[red]Deleted collection '{name}'[/red]")


@collections.command("stats")
@click.option("--name", required=True, help="Collection name")
def collections_stats(name: str):
    """Show collection statistics."""
    with get_client() as client:
        resp = client.get(f"/api/v1/collections/{name}/stats")
        resp.raise_for_status()

    data = resp.json()
    console.print(f"[bold]{data['name']}[/bold]")
    console.print(f"  Documents: {data['document_count']}")
    console.print(f"  Chunks:    {data['total_chunks']}")
    console.print(f"  Size:      {data['total_size_bytes']} bytes")


# --- Ingest ---
@cli.group()
def ingest():
    """Manage ingestion pipeline."""
    pass


@ingest.command("status")
def ingest_status():
    """Show ingestion pipeline status."""
    with get_client() as client:
        resp = client.get("/api/v1/ingest/status")
        resp.raise_for_status()

    data = resp.json()
    console.print(f"[bold]Queue depth:[/bold] {data.get('queue_depth', 'N/A')}")

    table = Table(title="Jobs by Status")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")

    for status, count in data.get("jobs", {}).items():
        style = "green" if status == "completed" else "red" if status in ("failed", "dead_letter") else ""
        table.add_row(status, str(count), style=style)

    console.print(table)


@ingest.command("job")
@click.option("--job-id", required=True, help="Job ID")
def ingest_job(job_id: str):
    """Get status of a specific job."""
    with get_client() as client:
        resp = client.get(f"/api/v1/ingest/jobs/{job_id}")
        resp.raise_for_status()

    console.print_json(json.dumps(resp.json(), indent=2))


# --- Users ---
@cli.group()
def users():
    """Manage users and access."""
    pass


@users.command("list")
def users_list():
    """List all users."""
    with get_client() as client:
        resp = client.get("/api/v1/users")
        resp.raise_for_status()

    table = Table(title="Users")
    table.add_column("Username", style="cyan")
    table.add_column("Clearance")
    table.add_column("Active")
    table.add_column("Created")

    for u in resp.json():
        active_style = "green" if u["is_active"] else "red"
        table.add_row(
            u["username"],
            u["clearance"],
            f"[{active_style}]{u['is_active']}[/{active_style}]",
            u.get("created_at", "")[:19],
        )

    console.print(table)


@users.command("create")
@click.option("--username", required=True, help="Username")
@click.option("--clearance", default="public", type=click.Choice(["public", "internal", "confidential", "restricted"]))
def users_create(username: str, clearance: str):
    """Create a new user and generate API key."""
    with get_client() as client:
        resp = client.post("/api/v1/users", json={"username": username, "clearance": clearance})
        resp.raise_for_status()

    data = resp.json()
    console.print(f"[green]Created user '{username}' with clearance '{clearance}'[/green]")
    console.print(f"[bold yellow]API Key: {data['api_key']}[/bold yellow]")
    console.print("[red]Store this key securely. It will NOT be shown again.[/red]")


@users.command("update")
@click.option("--user-id", required=True, help="User UUID")
@click.option("--clearance", type=click.Choice(["public", "internal", "confidential", "restricted"]))
def users_update(user_id: str, clearance: str | None):
    """Update a user's clearance."""
    body = {}
    if clearance:
        body["clearance"] = clearance

    with get_client() as client:
        resp = client.patch(f"/api/v1/users/{user_id}", json=body)
        resp.raise_for_status()

    console.print(f"[green]Updated user {user_id}[/green]")


# --- Audit ---
@cli.command("audit")
@click.option("--user", default=None, help="Filter by username")
@click.option("--since", default=None, help="Since datetime (ISO 8601)")
@click.option("--limit", default=20, help="Max entries")
def audit_cmd(user: str | None, since: str | None, limit: int):
    """Query audit log."""
    params: dict = {"limit": limit}
    if user:
        params["username"] = user
    if since:
        params["since"] = since

    with get_client() as client:
        resp = client.get("/api/v1/audit", params=params)
        resp.raise_for_status()

    table = Table(title="Audit Log")
    table.add_column("Time", style="dim")
    table.add_column("User", style="cyan")
    table.add_column("Query")
    table.add_column("Retrieved", justify="right")
    table.add_column("Redacted", justify="right", style="red")
    table.add_column("Duration", justify="right")

    for entry in resp.json():
        table.add_row(
            entry.get("created_at", "")[:19],
            entry.get("username", ""),
            entry.get("query_text", "")[:60],
            str(entry.get("chunks_retrieved", 0)),
            str(entry.get("chunks_redacted", 0)),
            f"{entry.get('query_duration_ms', 0):.0f}ms",
        )

    console.print(table)


# --- Health ---
@cli.command("health")
@click.option("--component", default=None, help="Check specific component")
def health_cmd(component: str | None):
    """Check system health."""
    with get_client() as client:
        resp = client.get("/health/ready")

    data = resp.json()
    overall = data.get("status", "unknown")
    style = "green" if overall == "ok" else "yellow" if overall == "degraded" else "red"

    console.print(f"[bold {style}]Status: {overall}[/bold {style}]")

    for name, status in data.get("checks", {}).items():
        if component and name != component:
            continue
        icon = "[green]OK[/green]" if status == "ok" else f"[red]{status}[/red]"
        console.print(f"  {name}: {icon}")


# --- Config ---
@cli.command("config")
def config_cmd():
    """Show active configuration (secrets redacted)."""
    with get_client() as client:
        resp = client.get("/health")
        resp.raise_for_status()

    console.print("[bold]VaultMind Configuration[/bold]")
    console.print(f"  API URL: {client.base_url}")
    console.print(f"  API Status: {resp.json().get('status', 'unknown')}")


if __name__ == "__main__":
    cli()
