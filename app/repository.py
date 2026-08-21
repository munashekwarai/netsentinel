"""SQLite persistence for check definitions, results, and alert counters."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import AlertState, CheckKind, CheckResult, CheckSpec


class Repository:
    def __init__(self, path: str = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
                target TEXT NOT NULL, port INTEGER, timeout_seconds REAL NOT NULL,
                expected_status INTEGER NOT NULL, failure_threshold INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1, consecutive_failures INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY, check_id INTEGER NOT NULL REFERENCES checks(id) ON DELETE CASCADE,
                healthy INTEGER NOT NULL, latency_ms REAL NOT NULL, detail_json TEXT NOT NULL,
                checked_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS results_check_time ON results(check_id, checked_at DESC);
        """)

    def add_check(self, spec: CheckSpec) -> CheckSpec:
        cursor = self.db.execute(
            """INSERT INTO checks(name,kind,target,port,timeout_seconds,expected_status,failure_threshold,enabled)
               VALUES(?,?,?,?,?,?,?,?)""",
            (spec.name, spec.kind.value, spec.target, spec.port, spec.timeout_seconds,
             spec.expected_status, spec.failure_threshold, int(spec.enabled)),
        )
        self.db.commit()
        return self.get_check(cursor.lastrowid)

    def get_check(self, check_id: int) -> CheckSpec:
        row = self.db.execute("SELECT * FROM checks WHERE id=?", (check_id,)).fetchone()
        if row is None:
            raise KeyError(f"check {check_id} not found")
        return self._spec(row)

    def list_checks(self, enabled_only: bool = False) -> list[CheckSpec]:
        sql = "SELECT * FROM checks" + (" WHERE enabled=1" if enabled_only else "") + " ORDER BY id"
        return [self._spec(row) for row in self.db.execute(sql)]

    def set_enabled(self, check_id: int, enabled: bool) -> CheckSpec:
        with self.db:
            cursor = self.db.execute("UPDATE checks SET enabled=? WHERE id=?", (int(enabled), check_id))
        if cursor.rowcount == 0:
            raise KeyError(f"check {check_id} not found")
        return self.get_check(check_id)

    def delete_check(self, check_id: int) -> None:
        with self.db:
            cursor = self.db.execute("DELETE FROM checks WHERE id=?", (check_id,))
        if cursor.rowcount == 0:
            raise KeyError(f"check {check_id} not found")

    def overview(self) -> dict:
        """Return real inventory and latest-result aggregates for the operator console."""
        checks = self.list_checks()
        states = [self.alert_state(check.id) for check in checks if check.id and check.enabled]
        latest = self.db.execute(
            """SELECT r.check_id,r.healthy,r.latency_ms,r.checked_at
               FROM results r JOIN (SELECT check_id,MAX(id) id FROM results GROUP BY check_id) x ON r.id=x.id"""
        ).fetchall()
        measured = [row for row in latest if row["latency_ms"] is not None]
        return {
            "total_checks": len(checks),
            "enabled_checks": sum(check.enabled for check in checks),
            "healthy_checks": sum(state is AlertState.OK for state in states),
            "warning_checks": sum(state is AlertState.WARNING for state in states),
            "alerting_checks": sum(state is AlertState.ALERT for state in states),
            "average_latency_ms": round(sum(row["latency_ms"] for row in measured) / len(measured), 1) if measured else None,
            "latest_run_at": max((row["checked_at"] for row in latest), default=None),
        }

    def record(self, result: CheckResult) -> AlertState:
        if result.check_id is None:
            raise ValueError("persisted results require a check_id")
        with self.db:
            self.db.execute(
                "INSERT INTO results(check_id,healthy,latency_ms,detail_json,checked_at) VALUES(?,?,?,?,?)",
                (result.check_id, int(result.healthy), result.latency_ms,
                 json.dumps(result.detail, sort_keys=True), result.checked_at.isoformat()),
            )
            self.db.execute(
                """UPDATE checks SET consecutive_failures=
                   CASE WHEN ? THEN 0 ELSE consecutive_failures + 1 END WHERE id=?""",
                (int(result.healthy), result.check_id),
            )
        return self.alert_state(result.check_id)

    def alert_state(self, check_id: int) -> AlertState:
        row = self.db.execute(
            "SELECT consecutive_failures,failure_threshold FROM checks WHERE id=?", (check_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"check {check_id} not found")
        failures, threshold = row
        if failures == 0:
            return AlertState.OK
        return AlertState.ALERT if failures >= threshold else AlertState.WARNING

    def history(self, check_id: int, limit: int = 100) -> list[dict]:
        limit = max(1, min(limit, 1000))
        rows = self.db.execute(
            "SELECT * FROM results WHERE check_id=? ORDER BY checked_at DESC LIMIT ?", (check_id, limit)
        )
        return [{"healthy": bool(row["healthy"]), "latency_ms": row["latency_ms"],
                 "detail": json.loads(row["detail_json"]), "checked_at": row["checked_at"]} for row in rows]

    def uptime(self, check_id: int, limit: int = 100) -> float | None:
        values = self.history(check_id, limit)
        return round(sum(item["healthy"] for item in values) / len(values) * 100, 2) if values else None

    @staticmethod
    def _spec(row: sqlite3.Row) -> CheckSpec:
        return CheckSpec(id=row["id"], name=row["name"], kind=CheckKind(row["kind"]),
                         target=row["target"], port=row["port"], timeout_seconds=row["timeout_seconds"],
                         expected_status=row["expected_status"], failure_threshold=row["failure_threshold"],
                         enabled=bool(row["enabled"]))
