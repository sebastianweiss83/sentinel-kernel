#!/usr/bin/env python3
"""
benchmarks/benchmark_trace.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Micro-benchmarks for Sentinel trace emission.

Measures:
  - Traces per second (SQLite in-memory)
  - Traces per second (SQLite on-disk)
  - Traces per second (Filesystem)
  - Latency overhead of @sentinel.trace decorator
  - Memory usage per 1000 traces

Documented targets (see docs/performance.md):
  SQLite in-memory  : >2000 traces/second
  SQLite on-disk    : >1000 traces/second
  Filesystem        : >2000 traces/second
  Decorator overhead: <1ms per call

Run:
    python benchmarks/benchmark_trace.py
    python benchmarks/benchmark_trace.py --json  # machine-readable

Exit code is 0 unless --regress-check is passed AND the current run
is >20% below the documented baseline.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
import tracemalloc
from dataclasses import asdict, dataclass
from typing import Any

from sentinel import Sentinel
from sentinel.storage.filesystem import FilesystemStorage
from sentinel.storage.sqlite import SQLiteStorage

BASELINE = {
    "sqlite_memory_traces_per_sec": 2000.0,
    "sqlite_disk_traces_per_sec": 1000.0,
    "filesystem_traces_per_sec": 2000.0,
    "decorator_overhead_ms_p50": 1.0,
    "memory_per_1000_traces_kb": 2048.0,  # 2 MiB — generous
}


@dataclass
class BenchmarkResult:
    name: str
    value: float
    unit: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _time_it(fn: Any, n: int = 1000) -> float:
    """Return elapsed seconds for n invocations."""
    start = time.perf_counter()
    for _ in range(n):
        fn()
    return time.perf_counter() - start


def _make_sentinel(storage: Any) -> Sentinel:
    return Sentinel(storage=storage, project="bench")


def _agent_fn(sentinel: Sentinel) -> Any:
    @sentinel.trace
    def agent(x: int) -> dict[str, int]:
        return {"x": x, "result": x * 2}

    return agent


def bench_sqlite_memory(n: int = 1000) -> BenchmarkResult:
    sentinel = _make_sentinel(SQLiteStorage(":memory:"))
    agent = _agent_fn(sentinel)
    elapsed = _time_it(lambda: agent(x=1), n=n)
    return BenchmarkResult(
        name="sqlite_memory_traces_per_sec",
        value=n / elapsed,
        unit="traces/sec",
    )


def bench_sqlite_disk(n: int = 500) -> BenchmarkResult:
    with tempfile.TemporaryDirectory() as d:
        sentinel = _make_sentinel(SQLiteStorage(f"{d}/bench.db"))
        agent = _agent_fn(sentinel)
        elapsed = _time_it(lambda: agent(x=1), n=n)
    return BenchmarkResult(
        name="sqlite_disk_traces_per_sec",
        value=n / elapsed,
        unit="traces/sec",
    )


def bench_filesystem(n: int = 1000) -> BenchmarkResult:
    with tempfile.TemporaryDirectory() as d:
        sentinel = _make_sentinel(FilesystemStorage(f"{d}/fs"))
        agent = _agent_fn(sentinel)
        elapsed = _time_it(lambda: agent(x=1), n=n)
    return BenchmarkResult(
        name="filesystem_traces_per_sec",
        value=n / elapsed,
        unit="traces/sec",
    )


def bench_decorator_overhead(n: int = 1000) -> BenchmarkResult:
    """Measure wall-clock overhead of @sentinel.trace vs plain call."""
    sentinel = _make_sentinel(SQLiteStorage(":memory:"))

    @sentinel.trace
    def traced(x: int) -> int:
        return x * 2

    def plain(x: int) -> int:
        return x * 2

    traced_elapsed = _time_it(lambda: traced(x=1), n=n)
    plain_elapsed = _time_it(lambda: plain(1), n=n)
    overhead_ms = (traced_elapsed - plain_elapsed) / n * 1000.0
    return BenchmarkResult(
        name="decorator_overhead_ms_p50",
        value=max(0.0, overhead_ms),
        unit="ms/call",
    )


def bench_memory_per_1000(n: int = 1000) -> BenchmarkResult:
    sentinel = _make_sentinel(SQLiteStorage(":memory:"))
    agent = _agent_fn(sentinel)
    tracemalloc.start()
    baseline, _ = tracemalloc.get_traced_memory()
    for _ in range(n):
        agent(x=1)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return BenchmarkResult(
        name="memory_per_1000_traces_kb",
        value=(peak - baseline) / 1024.0,
        unit="KiB/1000 traces",
    )


def run_all() -> list[BenchmarkResult]:
    return [
        bench_sqlite_memory(),
        bench_sqlite_disk(),
        bench_filesystem(),
        bench_decorator_overhead(),
        bench_memory_per_1000(),
    ]


def _check_regression(results: list[BenchmarkResult]) -> list[str]:
    failures: list[str] = []
    for r in results:
        baseline = BASELINE.get(r.name)
        if baseline is None:
            continue
        if r.name.endswith("_traces_per_sec"):
            # Regression is >20% below baseline
            if r.value < baseline * 0.8:
                failures.append(
                    f"{r.name}: {r.value:.1f} < {baseline * 0.8:.1f} (baseline {baseline})"
                )
        else:
            # Regression is >20% above baseline (more is worse)
            if r.value > baseline * 1.2:
                failures.append(
                    f"{r.name}: {r.value:.2f} > {baseline * 1.2:.2f} (baseline {baseline})"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--regress-check", action="store_true")
    args = parser.parse_args()

    results = run_all()

    if args.json:
        print(
            json.dumps(
                {"results": [r.to_dict() for r in results]},
                indent=2,
            )
        )
    else:
        print("=" * 60)
        print("  SENTINEL BENCHMARK RESULTS")
        print("=" * 60)
        for r in results:
            baseline = BASELINE.get(r.name)
            marker = ""
            if baseline is not None:
                if r.name.endswith("_traces_per_sec"):
                    marker = "  ✓" if r.value >= baseline * 0.8 else "  ✗"
                else:
                    marker = "  ✓" if r.value <= baseline * 1.2 else "  ✗"
            print(f"  {r.name:40} {r.value:12.2f} {r.unit}{marker}")
        print("=" * 60)

    if args.regress_check:
        failures = _check_regression(results)
        if failures:
            print("REGRESSIONS DETECTED:")
            for f in failures:
                print(f"  {f}")
            return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
