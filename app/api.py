"""NetSentinel REST API."""
from __future__ import annotations

import os
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .logging import configure
from .models import CheckKind, CheckSpec
from .monitor import Monitor
from .repository import Repository


class CheckInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: CheckKind
    target: str = Field(min_length=1, max_length=2048)
    port: int | None = Field(default=None, ge=1, le=65535)
    timeout_seconds: float = Field(default=5, ge=0.1, le=30)
    expected_status: int = Field(default=200, ge=100, le=599)
    failure_threshold: int = Field(default=3, ge=1, le=100)


repository = Repository(os.getenv("NETSENTINEL_DB", ":memory:"))
monitor = Monitor(repository)
configure(os.getenv("LOG_LEVEL", "INFO"))
app = FastAPI(title="NetSentinel", version="0.2.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "monitor_state": monitor.overall_state().value}


@app.post("/checks", status_code=201)
def create_check(value: CheckInput) -> dict:
    try:
        spec = repository.add_check(CheckSpec(**value.model_dump()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "a check with that name already exists") from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return {"id": spec.id, **value.model_dump(mode="json")}


@app.get("/checks")
def list_checks() -> list[dict]:
    return [{"id": item.id, "name": item.name, "kind": item.kind.value, "target": item.target,
             "port": item.port, "enabled": item.enabled} for item in repository.list_checks()]


@app.post("/checks/{check_id}/run")
def run_check(check_id: int) -> dict:
    try:
        return monitor.run_check(check_id).to_dict()
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from None


@app.get("/checks/{check_id}/history")
def history(check_id: int, limit: int = Query(default=100, ge=1, le=1000)) -> dict:
    try:
        spec = repository.get_check(check_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from None
    return {"check_id": check_id, "name": spec.name, "uptime_percent": repository.uptime(check_id, limit),
            "alert_state": repository.alert_state(check_id).value,
            "results": repository.history(check_id, limit)}


@app.post("/runs")
def run_all() -> dict:
    outcomes = monitor.run_all()
    return {"monitor_state": monitor.overall_state().value,
            "checks": [outcome.to_dict() for outcome in outcomes]}
