"""
sentinel.integrations.prometheus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Prometheus textfile collector exporter for Sentinel.

Writes a ``.prom`` file that Prometheus' node-exporter textfile
collector can pick up. No network server runs from Sentinel — the
file is the interface, which is the sovereign-friendly way to
expose metrics (no inbound listener, no cloud dep, no special
firewall rules).

Metrics emitted:

  sentinel_sovereignty_score           gauge   0.0 – 1.0
  sentinel_days_to_enforcement         gauge   days until 2026-08-02
  sentinel_kill_switch_active          gauge   0 | 1
  sentinel_decisions_total             gauge   labels: policy_result, agent
  sentinel_latency_ms_p50              gauge   labels: agent
  sentinel_latency_ms_p95              gauge   labels: agent
  sentinel_latency_ms_p99              gauge   labels: agent
  sentinel_test_coverage_ratio         gauge   0.0 – 1.0 (operator-supplied)
  sentinel_manifesto_score             gauge   0.0 – 1.0 (if manifesto supplied)

Sovereignty posture:
  - prometheus_client is CNCF / Prometheus project open source
  - Jurisdiction: Neutral (CNCF)
  - CLOUD Act exposure: None
  - Air-gap capable: Yes
  - Critical path: No — runs in a background thread and writes a
    local file; failures are logged and swallowed.

Install: pip install sentinel-kernel[prometheus]

Usage::

    from sentinel.integrations.prometheus import PrometheusExporter

    exporter = PrometheusExporter(
        sentinel=my_sentinel,
        output_path="/var/lib/prometheus/sentinel.prom",
        interval_seconds=15,
    )
    exporter.start()  # background thread

    # ... agent runs ...

    exporter.stop()  # or let daemon thread exit with the process
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.manifesto.base import SentinelManifesto


log = logging.getLogger("sentinel.prometheus")

_MISSING_DEP_MESSAGE = (
    "PrometheusExporter requires prometheus_client. Install the extra:\n"
    "    pip install sentinel-kernel[prometheus]"
)


def _import_prometheus_client() -> Any:
    try:
        import prometheus_client  # noqa: F401
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return prometheus_client


class PrometheusExporter:
    """
    Periodic Prometheus textfile exporter.

    On every tick, the exporter:
      1. Runs the ``RuntimeScanner`` and reads ``sovereignty_score``.
      2. Runs the ``EUAIActChecker`` and reads ``days_to_enforcement``.
      3. Reads ``sentinel.kill_switch_active`` (0 or 1).
      4. Queries recent traces and computes per-agent counts and
         latency percentiles.
      5. Optionally evaluates a manifesto and reads its overall score.
      6. Writes all metrics to the textfile atomically.

    The write is atomic: the file is written to a temporary path and
    renamed into place. This is how Prometheus textfile collectors
    expect to be updated without racing with the collector.
    """

    def __init__(
        self,
        sentinel: Sentinel,
        *,
        output_path: str | Path,
        interval_seconds: float = 15.0,
        manifesto: SentinelManifesto | None = None,
        test_coverage: float | None = None,
        query_window: int = 1000,
    ) -> None:
        _import_prometheus_client()

        self.sentinel = sentinel
        self.output_path = Path(output_path)
        self.interval_seconds = float(interval_seconds)
        self.manifesto = manifesto
        self.test_coverage = test_coverage
        self.query_window = int(query_window)

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Ensure target directory exists so the first write succeeds.
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    # ----- Lifecycle --------------------------------------------------------

    def start(self) -> None:
        """Start the background exporter thread (daemon)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="sentinel-prometheus-exporter",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the thread to stop and join briefly."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    # ----- Export loop ------------------------------------------------------

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.export_once()
            except Exception as exc:  # defensive — never crash the thread
                log.warning("Prometheus exporter tick failed: %s", exc)
            # Sleep in small increments so stop() is responsive
            remaining = self.interval_seconds
            while remaining > 0 and not self._stop.is_set():
                step = min(0.2, remaining)
                self._stop.wait(step)
                remaining -= step

    def export_once(self) -> Path:
        """
        Build a fresh registry, populate it from the current Sentinel
        state, and write it to the textfile. Returns the output path.

        Safe to call from tests. Not guarded by the background thread.
        """
        pc = _import_prometheus_client()
        registry = pc.CollectorRegistry()

        # ----- Scalar gauges -----
        g_sov = pc.Gauge(
            "sentinel_sovereignty_score",
            "Sovereignty score (fraction of installed packages with no CLOUD Act exposure)",
            registry=registry,
        )
        g_days = pc.Gauge(
            "sentinel_days_to_enforcement",
            "Days until EU AI Act Annex III enforcement (2 August 2026)",
            registry=registry,
        )
        g_kill = pc.Gauge(
            "sentinel_kill_switch_active",
            "Sentinel kill switch state (0 = normal, 1 = engaged)",
            registry=registry,
        )
        g_cov = pc.Gauge(
            "sentinel_test_coverage_ratio",
            "Operator-supplied test coverage ratio for the Sentinel deployment",
            registry=registry,
        )
        g_manifesto = pc.Gauge(
            "sentinel_manifesto_score",
            "Overall manifesto score (0.0 – 1.0)",
            registry=registry,
        )

        # ----- Labelled metrics -----
        g_decisions = pc.Gauge(
            "sentinel_decisions_total",
            "Count of decisions grouped by policy result and agent",
            ["policy_result", "agent"],
            registry=registry,
        )
        g_p50 = pc.Gauge(
            "sentinel_latency_ms_p50",
            "Decision latency p50 in milliseconds, per agent",
            ["agent"],
            registry=registry,
        )
        g_p95 = pc.Gauge(
            "sentinel_latency_ms_p95",
            "Decision latency p95 in milliseconds, per agent",
            ["agent"],
            registry=registry,
        )
        g_p99 = pc.Gauge(
            "sentinel_latency_ms_p99",
            "Decision latency p99 in milliseconds, per agent",
            ["agent"],
            registry=registry,
        )

        # ----- Populate from sentinel state -----
        self._populate_scalar(
            g_sov=g_sov,
            g_days=g_days,
            g_kill=g_kill,
            g_cov=g_cov,
            g_manifesto=g_manifesto,
        )
        self._populate_decisions(g_decisions, g_p50, g_p95, g_p99)

        # ----- Atomic write -----
        with self._lock:
            tmp_path = self.output_path.with_suffix(self.output_path.suffix + ".tmp")
            pc.write_to_textfile(str(tmp_path), registry)
            tmp_path.replace(self.output_path)

        return self.output_path

    # ----- Population helpers -----------------------------------------------

    def _populate_scalar(
        self,
        *,
        g_sov: Any,
        g_days: Any,
        g_kill: Any,
        g_cov: Any,
        g_manifesto: Any,
    ) -> None:
        from sentinel.compliance import EUAIActChecker
        from sentinel.scanner import RuntimeScanner

        try:
            score = RuntimeScanner().scan().sovereignty_score
            g_sov.set(score)
        except Exception as exc:
            log.warning("sovereignty_score unavailable: %s", exc)
            g_sov.set(0.0)

        try:
            compliance = EUAIActChecker().check(self.sentinel)
            g_days.set(compliance.days_to_enforcement)
        except Exception as exc:
            log.warning("days_to_enforcement unavailable: %s", exc)
            g_days.set(0)

        kill_active = 1 if getattr(self.sentinel, "kill_switch_active", False) else 0
        g_kill.set(kill_active)

        if self.test_coverage is not None:
            g_cov.set(float(self.test_coverage))
        else:
            g_cov.set(0.0)

        if self.manifesto is not None:
            try:
                report = self.manifesto.check(sentinel=self.sentinel)
                g_manifesto.set(report.overall_score)
            except Exception as exc:
                log.warning("manifesto score unavailable: %s", exc)
                g_manifesto.set(0.0)
        else:
            g_manifesto.set(0.0)

    def _populate_decisions(
        self,
        g_decisions: Any,
        g_p50: Any,
        g_p95: Any,
        g_p99: Any,
    ) -> None:
        traces = self.sentinel.query(limit=self.query_window)

        counts: dict[tuple[str, str], int] = defaultdict(int)
        latencies: dict[str, list[float]] = defaultdict(list)

        for t in traces:
            if t.policy_evaluation is not None:
                result = t.policy_evaluation.result.value
            else:
                result = "NOT_EVALUATED"
            counts[(result, t.agent)] += 1
            if t.latency_ms is not None:
                latencies[t.agent].append(float(t.latency_ms))

        for (result, agent), n in counts.items():
            g_decisions.labels(policy_result=result, agent=agent).set(n)

        for agent, samples in latencies.items():
            if not samples:
                continue
            g_p50.labels(agent=agent).set(_percentile(samples, 0.50))
            g_p95.labels(agent=agent).set(_percentile(samples, 0.95))
            g_p99.labels(agent=agent).set(_percentile(samples, 0.99))


def _percentile(values: list[float], p: float) -> float:
    """Simple inclusive-linear percentile. Matches numpy's default."""
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    if p <= 0:
        return float(min(values))
    if p >= 1:
        return float(max(values))
    # Use statistics.quantiles for n=100 and index — deterministic and
    # dependency-free.
    sorted_values = sorted(values)
    # Linear interpolation, equivalent to numpy percentile with method='linear'
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return float(sorted_values[int(k)])
    return float(
        sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)
    )
