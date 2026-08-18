"""Minimal JSON logging without a third-party logging dependency."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                   "logger": record.name, "event": record.getMessage()}
        for key in ("check_id", "healthy", "latency_ms", "alert_state"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def configure(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("netsentinel")
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
