"""Operator CLI for one-shot diagnostics and persisted monitoring."""
from __future__ import annotations

import json
import os

import typer

from . import core
from .logging import configure
from .monitor import Monitor, load_config
from .repository import Repository

app = typer.Typer(no_args_is_help=True, help="Lightweight service monitoring and diagnostics")


def emit(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, default=str))


@app.command()
def dns(host: str) -> None:
    """Resolve all addresses for HOST."""
    emit(core.dns(host).to_dict())


@app.command()
def port(host: str, port: int = typer.Argument(min=1, max=65535)) -> None:
    """Test a TCP service."""
    emit(core.tcp(host, port).to_dict())


@app.command("https")
def check_http(url: str) -> None:
    """Test an HTTP or HTTPS endpoint."""
    emit(core.http(url).to_dict())


@app.command()
def check(host: str) -> None:
    """Run DNS, TCP/443, and TLS diagnostics."""
    results = [core.dns(host), core.tcp(host, 443), core.tls(host)]
    emit({"state": core.state(results), "checks": [result.to_dict() for result in results]})


@app.command()
def run(config: str, database: str = "./data/netsentinel.db") -> None:
    """Import CONFIG JSON and execute all enabled checks once."""
    repository = Repository(database)
    existing = {item.name for item in repository.list_checks()}
    for spec in load_config(config):
        if spec.name not in existing:
            repository.add_check(spec)
    emit({"state": Monitor(repository).overall_state().value,
          "outcomes": [value.to_dict() for value in Monitor(repository).run_all()]})


@app.command()
def watch(config: str, database: str = "./data/netsentinel.db", interval: int = 60) -> None:
    """Continuously execute configured checks at INTERVAL seconds."""
    repository = Repository(database)
    existing = {item.name for item in repository.list_checks()}
    for spec in load_config(config):
        if spec.name not in existing:
            repository.add_check(spec)
    Monitor(repository).run_forever(interval)


@app.command()
def history(check_id: int, database: str = "./data/netsentinel.db", limit: int = 20) -> None:
    """Show recent evidence and uptime for a configured check."""
    repository = Repository(database)
    emit({"check_id": check_id, "uptime_percent": repository.uptime(check_id, limit),
          "alert_state": repository.alert_state(check_id).value,
          "results": repository.history(check_id, limit)})


if __name__ == "__main__":
    configure(os.getenv("LOG_LEVEL", "INFO"))
    app()
