"""Backward-compatible one-shot helpers backed by the reusable probe engine."""
from __future__ import annotations

from .models import AlertState, CheckKind, CheckResult, CheckSpec, HealthState
from .probes import ProbeRunner
from .repository import Repository

Result = CheckResult
_runner = ProbeRunner()


def dns(host: str) -> CheckResult:
    return _runner.run(CheckSpec(name=f"dns:{host}", kind=CheckKind.DNS, target=host))


def tcp(host: str, port: int, timeout: float = 3) -> CheckResult:
    return _runner.run(CheckSpec(name=f"tcp:{host}:{port}", kind=CheckKind.TCP, target=host,
                                 port=port, timeout_seconds=timeout))


def http(url: str, timeout: float = 5) -> CheckResult:
    return _runner.run(CheckSpec(name=f"http:{url}", kind=CheckKind.HTTP, target=url,
                                 timeout_seconds=timeout))


def tls(host: str, port: int = 443, timeout: float = 3) -> CheckResult:
    return _runner.run(CheckSpec(name=f"tls:{host}:{port}", kind=CheckKind.TLS, target=host,
                                 port=port, timeout_seconds=timeout))


def icmp(host: str, timeout: float = 3) -> CheckResult:
    return _runner.run(CheckSpec(name=f"icmp:{host}", kind=CheckKind.ICMP, target=host,
                                 timeout_seconds=timeout))


def state(results: list[CheckResult]) -> str:
    failures = sum(not result.healthy for result in results)
    return (HealthState.HEALTHY if failures == 0 else
            HealthState.DEGRADED if failures < len(results) else HealthState.DOWN).value


class History:
    """Compatibility wrapper for ad-hoc, non-configured results."""
    def __init__(self, path: str = ":memory:") -> None:
        import sqlite3
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS results(target TEXT, healthy INTEGER)")

    def record(self, result: CheckResult) -> None:
        self.db.execute("INSERT INTO results VALUES(?,?)", (result.target, int(result.healthy)))
        self.db.commit()

    def uptime(self, target: str, limit: int = 100) -> float | None:
        rows = self.db.execute("SELECT healthy FROM results WHERE target=? LIMIT ?", (target, limit)).fetchall()
        return round(sum(row[0] for row in rows) / len(rows) * 100, 2) if rows else None


class AlertTracker:
    def __init__(self, failure_threshold: int = 3) -> None:
        self.threshold = failure_threshold
        self.failures: dict[str, int] = {}

    def observe(self, result: CheckResult) -> str:
        count = 0 if result.healthy else self.failures.get(result.target, 0) + 1
        self.failures[result.target] = count
        return (AlertState.ALERT if count >= self.threshold else
                AlertState.WARNING if count else AlertState.OK).value
