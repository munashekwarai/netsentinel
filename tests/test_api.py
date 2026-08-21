from fastapi.testclient import TestClient

from app import api
from app.models import CheckResult
from app.monitor import Monitor
from app.repository import Repository


class HealthyProbe:
    def run(self, spec):
        return CheckResult(check_id=spec.id, check_name=spec.name, kind=spec.kind,
                           target=spec.target, healthy=True, latency_ms=8.2,
                           detail={"addresses": ["192.0.2.2"]})


def client(monkeypatch):
    repository = Repository()
    monkeypatch.setattr(api, "repository", repository)
    monkeypatch.setattr(api, "monitor", Monitor(repository, HealthyProbe()))
    return TestClient(api.app)


def test_create_list_run_and_history(monkeypatch):
    http = client(monkeypatch)
    created = http.post("/checks", json={"name": "resolver", "kind": "dns",
                                               "target": "example.com", "failure_threshold": 2})
    assert created.status_code == 201
    check_id = created.json()["id"]
    assert http.get("/checks").json()[0]["name"] == "resolver"
    run = http.post(f"/checks/{check_id}/run")
    assert run.status_code == 200 and run.json()["alert_state"] == "OK"
    history = http.get(f"/checks/{check_id}/history").json()
    assert history["uptime_percent"] == 100.0
    assert history["results"][0]["detail"]["addresses"] == ["192.0.2.2"]


def test_duplicate_name_and_missing_check_are_structured(monkeypatch):
    http = client(monkeypatch)
    payload = {"name": "resolver", "kind": "dns", "target": "example.com"}
    assert http.post("/checks", json=payload).status_code == 201
    assert http.post("/checks", json=payload).status_code == 409
    assert http.post("/checks/404/run").status_code == 404


def test_api_rejects_invalid_tcp_definition(monkeypatch):
    http = client(monkeypatch)
    response = http.post("/checks", json={"name": "database", "kind": "tcp",
                                                "target": "db.internal"})
    assert response.status_code == 422


def test_overview_state_controls_and_delete(monkeypatch):
    http = client(monkeypatch)
    check_id = http.post("/checks", json={"name": "resolver", "kind": "dns", "target": "example.com"}).json()["id"]
    empty = http.get("/overview").json()
    assert empty["total_checks"] == 1 and empty["average_latency_ms"] is None

    assert http.post(f"/checks/{check_id}/run").status_code == 200
    measured = http.get("/overview").json()
    assert measured["healthy_checks"] == 1 and measured["average_latency_ms"] == 8.2
    listed = http.get("/checks").json()[0]
    assert listed["latest_result"]["latency_ms"] == 8.2

    assert http.patch(f"/checks/{check_id}", json={"enabled": False}).json()["enabled"] is False
    assert http.delete(f"/checks/{check_id}").status_code == 204
    assert http.get("/checks").json() == []


def test_operator_console_and_assets_are_served(monkeypatch):
    http = client(monkeypatch)
    page = http.get("/")
    assert page.status_code == 200
    assert "Service health" in page.text and "No monitors configured" in page.text
    assert http.get("/assets/app.css").status_code == 200
    assert http.get("/assets/app.js").status_code == 200
