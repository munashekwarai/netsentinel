import io
import urllib.error
from unittest.mock import patch

from app.models import CheckKind, CheckSpec
from app.probes import ProbeRunner


class Response:
    status = 204
    url = "https://service.example/health"
    headers = {"content-type": "application/json"}
    def __enter__(self): return self
    def __exit__(self, *args): return None


def test_http_probe_applies_expected_status():
    spec = CheckSpec(name="health", kind=CheckKind.HTTP,
                     target="https://service.example/health", expected_status=204)
    with patch("urllib.request.urlopen", return_value=Response()):
        value = ProbeRunner().run(spec)
    assert value.healthy
    assert value.detail["status"] == 204
    assert value.detail["final_url"].endswith("/health")


def test_http_probe_records_status_mismatch_as_unhealthy():
    spec = CheckSpec(name="health", kind=CheckKind.HTTP,
                     target="https://service.example/health", expected_status=200)
    with patch("urllib.request.urlopen", return_value=Response()):
        value = ProbeRunner().run(spec)
    assert not value.healthy
    assert value.detail["expected_status"] == 200


def test_probe_converts_bounded_network_failure_to_evidence():
    spec = CheckSpec(name="dns", kind=CheckKind.DNS, target="missing.invalid")
    with patch("socket.getaddrinfo", side_effect=OSError("resolver unavailable")):
        value = ProbeRunner().run(spec)
    assert not value.healthy
    assert value.detail == {"error": "OSError", "message": "resolver unavailable"}
