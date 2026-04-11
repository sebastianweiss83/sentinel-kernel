# Performance

Sentinel is designed to be low-overhead in the critical path. The
benchmarks in `benchmarks/benchmark_trace.py` characterise the
decorator, each storage backend, and the memory footprint.

## Documented baselines

These are the numbers a Sentinel 1.x deployment must meet on modern
commodity hardware (2020+ laptop or server). The CI regression job
fails if any measurement is more than 20% below baseline.

| Metric | Baseline | Notes |
|---|---|---|
| `sqlite_memory_traces_per_sec` | ≥ 2000 | In-memory SQLite, synchronous writes |
| `sqlite_disk_traces_per_sec` | ≥ 1000 | On-disk SQLite, fsync on commit |
| `filesystem_traces_per_sec` | ≥ 2000 | One file per trace, NDJSON format |
| `decorator_overhead_ms_p50` | ≤ 1.0 ms | Median wall-clock overhead of `@sentinel.trace` |
| `memory_per_1000_traces_kb` | ≤ 2048 KiB | Peak traced-memory delta for 1000 traces |

## Current results (v1.7.0, 2026-04-11)

Measured on: Apple Silicon M-series laptop, Python 3.14, SQLite 3.x.

| Metric | Measured | vs baseline |
|---|---|---|
| `sqlite_memory_traces_per_sec` | ~7000 | 3.5× faster |
| `sqlite_disk_traces_per_sec` | ~2100 | 2.1× faster |
| `filesystem_traces_per_sec` | ~2500 | 1.25× faster |
| `decorator_overhead_ms_p50` | ~0.14 ms | 7× better |
| `memory_per_1000_traces_kb` | ~27 KiB | 75× better |

## Running the benchmarks

```bash
python benchmarks/benchmark_trace.py
```

JSON output for CI:

```bash
python benchmarks/benchmark_trace.py --json
```

Regression check (exit 1 on a >20% regression):

```bash
python benchmarks/benchmark_trace.py --regress-check
```

## Performance notes by backend

### SQLite (reference deployment)

- **Mode:** synchronous `INSERT`, one row per trace, JSON payload.
- **Indices:** project, agent, policy_result, started_at.
- **Recommendations:** for throughput-critical deployments, use
  SQLite's WAL journal mode (`PRAGMA journal_mode=WAL`) and a
  larger page cache.

### Filesystem (air-gap reference)

- **Mode:** one NDJSON file per trace, atomic rename.
- **Recommendations:** use a filesystem with good small-file
  performance (XFS, ext4 with `dir_index`). Avoid network
  filesystems for latency-critical paths.

### PostgreSQL

- **Mode:** `INSERT ... RETURNING`, JSONB payload.
- **Recommendations:** pin a connection pool (5–20 connections),
  TLS required for any network hop, pg_crypto for at-rest
  encryption where BSI profiles require it.

## Profiling hints

If you suspect Sentinel is the bottleneck in your pipeline:

1. Run the benchmarks in your deployment environment — numbers vary
   by hardware and filesystem.
2. Use `cProfile` on a wrapped agent call to isolate the
   storage write from the policy evaluation:
   ```bash
   python -m cProfile -o /tmp/sentinel.prof your_agent_script.py
   python -m pstats /tmp/sentinel.prof
   ```
3. If you see high latency in the policy path, check whether the
   evaluator is making network calls (it should not — see the
   sovereignty rules in `.claude/rules/sovereignty-rules.md`).

## CI regression gate

A GitHub Actions job runs `benchmark_trace.py --regress-check` on
every push to main. A failure blocks the next release. The history
of results is committed as `benchmarks/history.ndjson` (one entry
per release).
