"""Monitoring orchestration and configuration loading."""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .models import AlertState, CheckKind, CheckResult, CheckSpec, HealthState
from .probes import ProbeRunner
from .repository import Repository

logger = logging.getLogger("netsentinel")


@dataclass(frozen=True, slots=True)
class RunOutcome:
    result: CheckResult
    alert_state: AlertState

    def to_dict(self) -> dict:
        return {**self.result.to_dict(), "alert_state": self.alert_state.value}


class Monitor:
    def __init__(self, repository: Repository, probes: ProbeRunner | None = None) -> None:
        self.repository = repository
        self.probes = probes or ProbeRunner()

    def run_check(self, check_id: int) -> RunOutcome:
        spec = self.repository.get_check(check_id)
        if not spec.enabled:
            raise ValueError("disabled checks cannot be run")
        result = self.probes.run(spec)
        alert = self.repository.record(result)
        logger.info("check_completed", extra={"check_id": check_id, "healthy": result.healthy,
                                               "latency_ms": result.latency_ms, "alert_state": alert.value})
        return RunOutcome(result, alert)

    def run_all(self) -> list[RunOutcome]:
        return [self.run_check(spec.id) for spec in self.repository.list_checks(enabled_only=True) if spec.id]

    def run_forever(self, interval_seconds: float = 60, max_cycles: int | None = None, sleep=time.sleep) -> None:
        """Execute enabled checks repeatedly; max_cycles makes the loop testable."""
        if not 1 <= interval_seconds <= 86400:
            raise ValueError("interval_seconds must be between 1 and 86400")
        cycles = 0
        while max_cycles is None or cycles < max_cycles:
            self.run_all()
            cycles += 1
            if max_cycles is None or cycles < max_cycles:
                sleep(interval_seconds)

    def overall_state(self) -> HealthState:
        checks = self.repository.list_checks(enabled_only=True)
        if not checks:
            return HealthState.DEGRADED
        states = [self.repository.alert_state(spec.id) for spec in checks if spec.id]
        if all(state is AlertState.OK for state in states):
            return HealthState.HEALTHY
        if all(state is AlertState.ALERT for state in states):
            return HealthState.DOWN
        return HealthState.DEGRADED


def load_config(path: str) -> list[CheckSpec]:
    """Load a bounded JSON check list; duplicate names are rejected."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("checks"), list):
        raise ValueError("configuration must contain a checks array")
    if len(payload["checks"]) > 1000:
        raise ValueError("configuration cannot exceed 1000 checks")
    specs = [CheckSpec(kind=CheckKind(item["kind"]), **{k: v for k, v in item.items() if k != "kind"})
             for item in payload["checks"]]
    names = [spec.name for spec in specs]
    if len(names) != len(set(names)):
        raise ValueError("check names must be unique")
    return specs
