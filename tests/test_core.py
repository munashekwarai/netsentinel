from datetime import datetime, timezone

import pytest

from app import core
from app.models import AlertState, CheckKind, CheckResult, CheckSpec, HealthState
from app.monitor import Monitor, load_config
from app.repository import Repository


def result(check_id: int, healthy: bool) -> CheckResult:
    return CheckResult(check_id=check_id, check_name="service", kind=CheckKind.TCP,
                       target="192.0.2.10", healthy=healthy, latency_ms=12.5,
                       detail={"port": 443}, checked_at=datetime.now(timezone.utc))


def test_dns_localhost_returns_address_evidence():
    value = core.dns("localhost")
    assert value.healthy
    assert value.detail["answer_count"] >= 1


def test_check_spec_rejects_invalid_operational_bounds():
    with pytest.raises(ValueError, match="port"):
        CheckSpec(name="bad", kind=CheckKind.TCP, target="host", port=0)
    with pytest.raises(ValueError, match="require a port"):
        CheckSpec(name="bad", kind=CheckKind.TCP, target="host")
    with pytest.raises(ValueError, match="timeout"):
        CheckSpec(name="bad", kind=CheckKind.DNS, target="host", timeout_seconds=90)


def test_repository_persists_history_uptime_and_alert_transition(tmp_path):
    repository = Repository(str(tmp_path / "monitor.db"))
    spec = repository.add_check(CheckSpec(name="gateway", kind=CheckKind.TCP,
                                          target="192.0.2.10", port=443, failure_threshold=2))
    assert repository.record(result(spec.id, False)) is AlertState.WARNING
    assert repository.record(result(spec.id, False)) is AlertState.ALERT
    assert repository.uptime(spec.id) == 0.0
    assert repository.history(spec.id)[0]["detail"] == {"port": 443}
    assert repository.record(result(spec.id, True)) is AlertState.OK
    assert repository.uptime(spec.id) == 33.33


def test_repository_uses_independent_failure_counters():
    repository = Repository()
    one = repository.add_check(CheckSpec(name="one", kind=CheckKind.DNS, target="one.example"))
    two = repository.add_check(CheckSpec(name="two", kind=CheckKind.DNS, target="two.example"))
    repository.record(result(one.id, False))
    repository.record(CheckResult(check_id=two.id, check_name="two", kind=CheckKind.DNS,
                                  target="two.example", healthy=True, latency_ms=1))
    assert repository.alert_state(one.id) is AlertState.WARNING
    assert repository.alert_state(two.id) is AlertState.OK


class FakeProbes:
    def __init__(self, healthy_by_name):
        self.healthy_by_name = healthy_by_name

    def run(self, spec):
        return CheckResult(check_id=spec.id, check_name=spec.name, kind=spec.kind,
                           target=spec.target, healthy=self.healthy_by_name[spec.name], latency_ms=4)


def test_monitor_runs_enabled_checks_and_calculates_overall_state():
    repository = Repository()
    first = repository.add_check(CheckSpec(name="dns", kind=CheckKind.DNS, target="example.com"))
    repository.add_check(CheckSpec(name="disabled", kind=CheckKind.DNS,
                                   target="example.org", enabled=False))
    monitor = Monitor(repository, FakeProbes({"dns": False}))
    outcomes = monitor.run_all()
    assert [item.result.check_id for item in outcomes] == [first.id]
    assert outcomes[0].alert_state is AlertState.WARNING
    assert monitor.overall_state() is HealthState.DEGRADED


def test_monitor_reaches_down_after_threshold():
    repository = Repository()
    spec = repository.add_check(CheckSpec(name="api", kind=CheckKind.HTTP,
                                          target="https://example.com", failure_threshold=2))
    monitor = Monitor(repository, FakeProbes({"api": False}))
    monitor.run_check(spec.id)
    monitor.run_check(spec.id)
    assert monitor.overall_state() is HealthState.DOWN


def test_config_loader_rejects_duplicates_and_accepts_real_specs(tmp_path):
    config = tmp_path / "checks.json"
    config.write_text('{"checks":[{"name":"dns","kind":"dns","target":"example.com"}]}')
    assert load_config(str(config))[0].kind is CheckKind.DNS
    config.write_text('{"checks":[{"name":"x","kind":"dns","target":"a"},'
                      '{"name":"x","kind":"dns","target":"b"}]}')
    with pytest.raises(ValueError, match="unique"):
        load_config(str(config))


def test_missing_check_is_explicit():
    with pytest.raises(KeyError, match="not found"):
        Repository().get_check(999)


def test_continuous_monitor_is_bounded_and_testable():
    repository = Repository()
    repository.add_check(CheckSpec(name="dns", kind=CheckKind.DNS, target="example.com"))
    monitor = Monitor(repository, FakeProbes({"dns": True}))
    sleeps = []
    monitor.run_forever(interval_seconds=5, max_cycles=3, sleep=sleeps.append)
    assert len(repository.history(1)) == 3
    assert sleeps == [5, 5]
