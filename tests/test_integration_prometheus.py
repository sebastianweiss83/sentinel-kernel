"""
tests/test_integration_prometheus.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for the Prometheus textfile exporter.

These tests require ``prometheus_client`` to be installed (it is
pulled in via the ``[dev]`` extra). When it is missing, we skip.
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage

pytest.importorskip("prometheus_client")

from sentinel.integrations.prometheus import (  # noqa: E402
    PrometheusExporter,
    _percentile,
)


def _make_sentinel(tmp_path: Path) -> Sentinel:
    def policy(inputs: dict) -> tuple[bool, str | None]:
        req = inputs.get("request", {})
        if req.get("deny"):
            return False, "denied_for_test"
        return True, None

    return Sentinel(
        storage=SQLiteStorage(str(tmp_path / "prom_test.db")),
        project="prom-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
    )


def _populate(sentinel: Sentinel) -> None:
    @sentinel.trace(policy="p.py", agent_name="procurement")
    def approve(request: dict) -> dict:
        return {"ok": True}

    for i in range(10):
        with contextlib.suppress(Exception):
            approve(request={"deny": i % 3 == 0, "amount": 100 + i})


# ---------------------------------------------------------------------------
# Missing-dep guard
# ---------------------------------------------------------------------------


def test_missing_prometheus_client_raises_helpful_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the import guard to raise by pretending prometheus_client
    # is not installed.
    import sentinel.integrations.prometheus as prom_mod

    def fake_import() -> None:
        raise ImportError(prom_mod._MISSING_DEP_MESSAGE)

    monkeypatch.setattr(prom_mod, "_import_prometheus_client", fake_import)
    with pytest.raises(ImportError) as excinfo:
        prom_mod.PrometheusExporter(
            sentinel=_make_sentinel(tmp_path),
            output_path=tmp_path / "metrics.prom",
        )
    assert "prometheus_client" in str(excinfo.value)
    assert "sentinel-kernel[prometheus]" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Core one-shot export
# ---------------------------------------------------------------------------


def test_prom_file_written(tmp_path: Path) -> None:
    sentinel = _make_sentinel(tmp_path)
    _populate(sentinel)

    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(sentinel=sentinel, output_path=out)
    written = exporter.export_once()

    assert written == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_metrics_contain_sovereignty_score(tmp_path: Path) -> None:
    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(
        sentinel=sentinel,
        output_path=out,
        test_coverage=0.96,
    )
    exporter.export_once()
    content = out.read_text()

    assert "sentinel_sovereignty_score" in content
    assert "sentinel_days_to_enforcement" in content
    assert "sentinel_kill_switch_active 0.0" in content
    assert "sentinel_test_coverage_ratio 0.96" in content


def test_metrics_contain_decision_counts(tmp_path: Path) -> None:
    sentinel = _make_sentinel(tmp_path)
    _populate(sentinel)

    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(sentinel=sentinel, output_path=out)
    exporter.export_once()
    content = out.read_text()

    assert "sentinel_decisions_total" in content
    # Label format: metric{label="value", ...}
    assert 'agent="procurement"' in content
    # Should have at least one ALLOW and one DENY row
    assert "ALLOW" in content
    assert "DENY" in content


def test_metrics_contain_latency_percentiles(tmp_path: Path) -> None:
    sentinel = _make_sentinel(tmp_path)
    _populate(sentinel)

    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(sentinel=sentinel, output_path=out)
    exporter.export_once()
    content = out.read_text()

    assert "sentinel_latency_ms_p50" in content
    assert "sentinel_latency_ms_p95" in content
    assert "sentinel_latency_ms_p99" in content


def test_metrics_reflect_kill_switch_state(tmp_path: Path) -> None:
    sentinel = _make_sentinel(tmp_path)

    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(sentinel=sentinel, output_path=out)

    # Initial: normal
    exporter.export_once()
    assert "sentinel_kill_switch_active 0.0" in out.read_text()

    # Engaged: 1
    sentinel.engage_kill_switch("test")
    exporter.export_once()
    assert "sentinel_kill_switch_active 1.0" in out.read_text()


def test_manifesto_score_emitted_when_supplied(tmp_path: Path) -> None:
    from sentinel.manifesto import EUOnly, Required, SentinelManifesto

    class _Clean(SentinelManifesto):
        jurisdiction = EUOnly()
        kill_switch = Required()

    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(
        sentinel=sentinel,
        output_path=out,
        manifesto=_Clean(),
    )
    exporter.export_once()
    content = out.read_text()
    assert "sentinel_manifesto_score" in content
    # A clean manifesto with two requirements should score > 0
    score_line = next(
        line for line in content.splitlines()
        if line.startswith("sentinel_manifesto_score ")
    )
    score = float(score_line.split()[1])
    assert score > 0.0


# ---------------------------------------------------------------------------
# Background thread lifecycle
# ---------------------------------------------------------------------------


def test_background_export_updates(tmp_path: Path) -> None:
    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(
        sentinel=sentinel,
        output_path=out,
        interval_seconds=0.1,
    )
    exporter.start()
    try:
        # Wait for first tick to produce the file
        for _ in range(40):
            if out.exists() and out.stat().st_size > 0:
                break
            time.sleep(0.05)
        assert out.exists()
        first_mtime = out.stat().st_mtime

        # Let at least one more tick happen
        time.sleep(0.3)

        # Touch: add a trace, next tick should include it
        _populate(sentinel)
        time.sleep(0.3)

        second_mtime = out.stat().st_mtime
        assert second_mtime >= first_mtime
    finally:
        exporter.stop()

    # After stop the thread is gone
    assert exporter._thread is None


def test_start_is_idempotent(tmp_path: Path) -> None:
    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(
        sentinel=sentinel,
        output_path=out,
        interval_seconds=0.1,
    )
    exporter.start()
    original_thread = exporter._thread
    exporter.start()  # should not start a second thread
    assert exporter._thread is original_thread
    exporter.stop()


# ---------------------------------------------------------------------------
# Percentile helper edge cases
# ---------------------------------------------------------------------------


def test_percentile_empty_returns_zero() -> None:
    assert _percentile([], 0.5) == 0.0


def test_percentile_single_value() -> None:
    assert _percentile([42.0], 0.95) == 42.0


def test_percentile_at_bounds() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(values, 0.0) == 1.0
    assert _percentile(values, 1.0) == 5.0


def test_percentile_interpolation() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    # p50 for 4 values = midpoint between 2 and 3 → 2.5
    assert _percentile(values, 0.5) == 2.5


def test_percentile_integer_index_hit() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    # p50 hits integer index 2 exactly → 30.0
    assert _percentile(values, 0.5) == 30.0


# ---------------------------------------------------------------------------
# Exception paths — defensive fallbacks
# ---------------------------------------------------------------------------


def test_export_tolerates_sovereignty_scan_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If RuntimeScanner raises, the exporter should log and emit 0.0."""
    from sentinel.scanner import RuntimeScanner

    def boom(self):  # noqa: ARG001
        raise RuntimeError("scanner kaboom")

    monkeypatch.setattr(RuntimeScanner, "scan", boom)

    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(sentinel=sentinel, output_path=out)
    exporter.export_once()
    assert "sentinel_sovereignty_score 0.0" in out.read_text()


def test_export_tolerates_compliance_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If EUAIActChecker raises, the exporter should log and emit 0."""
    import sentinel.integrations.prometheus as prom_mod

    class _BoomChecker:
        def check(self, sentinel):  # noqa: ARG002
            raise RuntimeError("checker kaboom")

    # The import is inside _populate_scalar, so we monkeypatch the
    # sentinel.compliance namespace's EUAIActChecker attribute.
    from sentinel import compliance

    monkeypatch.setattr(compliance, "EUAIActChecker", _BoomChecker)
    # Force the exporter to re-import from sentinel.compliance
    assert prom_mod  # keep ref

    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(sentinel=sentinel, output_path=out)
    exporter.export_once()
    assert "sentinel_days_to_enforcement 0.0" in out.read_text()


def test_export_tolerates_manifesto_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sentinel.manifesto import SentinelManifesto

    class _BoomManifesto(SentinelManifesto):
        def check(self, **kwargs):  # type: ignore[override] # noqa: ARG002
            raise RuntimeError("manifesto kaboom")

    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(
        sentinel=sentinel,
        output_path=out,
        manifesto=_BoomManifesto(),
    )
    exporter.export_once()
    assert "sentinel_manifesto_score 0.0" in out.read_text()


def test_export_handles_traces_without_policy_or_latency(tmp_path: Path) -> None:
    """Traces with no policy evaluation and no latency should not crash."""
    from sentinel import Sentinel as _Sentinel
    from sentinel.storage import SQLiteStorage as _Store

    sentinel = _Sentinel(
        storage=_Store(str(tmp_path / "bare.db")),
        project="bare",
    )

    @sentinel.trace
    def bare_agent(x: int) -> dict:
        return {"x": x}

    bare_agent(x=1)
    bare_agent(x=2)

    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(sentinel=sentinel, output_path=out)
    exporter.export_once()
    content = out.read_text()
    # policy_result label should be NOT_EVALUATED for these
    assert "NOT_EVALUATED" in content


def test_run_loop_handles_exception_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The background loop must swallow exceptions and keep running."""
    sentinel = _make_sentinel(tmp_path)
    out = tmp_path / "metrics.prom"
    exporter = PrometheusExporter(
        sentinel=sentinel,
        output_path=out,
        interval_seconds=0.05,
    )

    call_count = {"n": 0}

    original_export = exporter.export_once

    def flaky_export():
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("transient failure")
        return original_export()

    monkeypatch.setattr(exporter, "export_once", flaky_export)

    exporter.start()
    try:
        for _ in range(40):
            if call_count["n"] >= 2 and out.exists():
                break
            time.sleep(0.05)
    finally:
        exporter.stop()

    assert call_count["n"] >= 2  # loop survived the first exception


def test_import_guard_catches_missing_prometheus_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_import_prometheus_client should raise ImportError with a helpful message."""
    import builtins

    import sentinel.integrations.prometheus as prom_mod

    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "prometheus_client":
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    with pytest.raises(ImportError) as excinfo:
        prom_mod._import_prometheus_client()
    assert "sentinel-kernel[prometheus]" in str(excinfo.value)
