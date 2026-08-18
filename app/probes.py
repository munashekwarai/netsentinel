"""Bounded network probes with a uniform evidence model."""
from __future__ import annotations

import platform
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

from .models import CheckKind, CheckResult, CheckSpec


class ProbeRunner:
    """Dispatch check specifications to reusable protocol probes."""

    def run(self, spec: CheckSpec) -> CheckResult:
        handlers: dict[CheckKind, Callable[[CheckSpec], dict]] = {
            CheckKind.DNS: self._dns,
            CheckKind.TCP: self._tcp,
            CheckKind.HTTP: self._http,
            CheckKind.TLS: self._tls,
            CheckKind.ICMP: self._icmp,
        }
        started = time.perf_counter()
        try:
            detail = handlers[spec.kind](spec)
            healthy = bool(detail.pop("healthy", True))
        except (OSError, TimeoutError, ssl.SSLError, urllib.error.URLError, ValueError) as exc:
            healthy = False
            detail = {"error": type(exc).__name__, "message": str(exc)[:200]}
        return CheckResult(
            check_id=spec.id,
            check_name=spec.name,
            kind=spec.kind,
            target=spec.target,
            healthy=healthy,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            detail=detail,
        )

    @staticmethod
    def _dns(spec: CheckSpec) -> dict:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(spec.target, None)})
        if not addresses:
            raise OSError("resolver returned no addresses")
        return {"addresses": addresses, "answer_count": len(addresses)}

    @staticmethod
    def _tcp(spec: CheckSpec) -> dict:
        if spec.port is None:
            raise ValueError("TCP checks require a port")
        with socket.create_connection((spec.target, spec.port), spec.timeout_seconds) as connection:
            peer = connection.getpeername()
        return {"port": spec.port, "peer": peer[0]}

    @staticmethod
    def _http(spec: CheckSpec) -> dict:
        parsed = urlparse(spec.target)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("HTTP checks require an absolute http(s) URL")
        request = urllib.request.Request(
            spec.target,
            method="GET",
            headers={"User-Agent": "NetSentinel/0.2", "Accept": "*/*"},
        )
        try:
            with urllib.request.urlopen(request, timeout=spec.timeout_seconds) as response:
                status = response.status
                detail = {
                    "status": status,
                    "expected_status": spec.expected_status,
                    "content_type": response.headers.get("content-type"),
                    "final_url": response.url,
                }
        except urllib.error.HTTPError as exc:
            status = exc.code
            detail = {"status": status, "expected_status": spec.expected_status, "final_url": exc.url}
        detail["healthy"] = status == spec.expected_status
        return detail

    @staticmethod
    def _tls(spec: CheckSpec) -> dict:
        port = spec.port or 443
        context = ssl.create_default_context()
        with socket.create_connection((spec.target, port), spec.timeout_seconds) as raw:
            with context.wrap_socket(raw, server_hostname=spec.target) as secured:
                certificate = secured.getpeercert()
                cipher = secured.cipher()
        expires_at = datetime.strptime(
            certificate["notAfter"], "%b %d %H:%M:%S %Y %Z"
        ).replace(tzinfo=timezone.utc)
        remaining = (expires_at - datetime.now(timezone.utc)).days
        return {
            "port": port,
            "issuer": dict(item[0] for item in certificate.get("issuer", ())),
            "sans": [value for kind, value in certificate.get("subjectAltName", ()) if kind == "DNS"],
            "expires_at": expires_at.isoformat(),
            "days_remaining": remaining,
            "protocol": secured.version(),
            "cipher": cipher[0] if cipher else None,
            "healthy": remaining >= 0,
        }

    @staticmethod
    def _icmp(spec: CheckSpec) -> dict:
        windows = platform.system() == "Windows"
        command = ["ping", "-n" if windows else "-c", "1"]
        command += (["-w", str(int(spec.timeout_seconds * 1000))] if windows else ["-W", str(max(1, int(spec.timeout_seconds)))])
        command.append(spec.target)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds + 1,
            check=False,
        )
        return {"healthy": completed.returncode == 0, "return_code": completed.returncode}
