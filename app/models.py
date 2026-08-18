"""Domain models shared by probes, persistence, CLI, and API adapters."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class CheckKind(StrEnum):
    DNS = "dns"
    TCP = "tcp"
    HTTP = "http"
    TLS = "tls"
    ICMP = "icmp"


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"


class AlertState(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    ALERT = "ALERT"


@dataclass(frozen=True, slots=True)
class CheckSpec:
    """A validated, persistable monitoring definition."""

    name: str
    kind: CheckKind
    target: str
    port: int | None = None
    timeout_seconds: float = 5.0
    expected_status: int = 200
    failure_threshold: int = 3
    enabled: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or len(self.name) > 100:
            raise ValueError("name must contain 1 to 100 characters")
        if not self.target.strip() or len(self.target) > 2048:
            raise ValueError("target must contain 1 to 2048 characters")
        if self.port is not None and not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if not 0.1 <= self.timeout_seconds <= 30:
            raise ValueError("timeout_seconds must be between 0.1 and 30")
        if not 100 <= self.expected_status <= 599:
            raise ValueError("expected_status must be a valid HTTP status")
        if not 1 <= self.failure_threshold <= 100:
            raise ValueError("failure_threshold must be between 1 and 100")
        if self.kind in {CheckKind.TCP, CheckKind.TLS} and self.port is None:
            object.__setattr__(self, "port", 443 if self.kind is CheckKind.TLS else None)
        if self.kind is CheckKind.TCP and self.port is None:
            raise ValueError("TCP checks require a port")


@dataclass(frozen=True, slots=True)
class CheckResult:
    check_name: str
    kind: CheckKind
    target: str
    healthy: bool
    latency_ms: float
    detail: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    check_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["kind"] = self.kind.value
        value["checked_at"] = self.checked_at.isoformat()
        return value
