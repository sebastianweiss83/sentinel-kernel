# Migration guide: v1.x → v2.0

## tl;dr

**No breaking changes.** Every Sentinel v1.x API is preserved in
v2.0. You can upgrade by bumping the version pin:

```bash
pip install --upgrade sentinel-kernel==2.0.0
```

All tests in your existing suite should pass unchanged.

## What changed

### Status: Production / Stable

v2.0 is the first release explicitly stamped as **Production /
Stable** for BSI assessment. The `classifiers` in `pyproject.toml`
are updated accordingly. Practically: v1.x was already
production-quality, but v2.0 freezes the API-stability guarantees
documented in `docs/api-stability.md`.

### Every public API is STABLE unless marked BETA

See `docs/api-stability.md` for the full table. A handful of
surfaces remain BETA in 2.0:

- `sentinel.integrations.jupyter.SentinelWidget` — notebook
  rendering may tweak display modes based on feedback.
- `sentinel.policy.evaluator.PolicyVersion` — the field set may
  expand (e.g. `authors`, `review_cycle`).
- `sentinel.scanner.knowledge.PACKAGE_KNOWLEDGE` — the data itself
  grows continuously; the shape is frozen.

Everything else — the `Sentinel` class, `DecisionTrace`, storage
backends, manifesto types, compliance checkers, CLI subcommands —
is STABLE and safe to build against.

### Schema

`DecisionTrace.schema_version` is `"1.0.0"` as of v1.0.0 and
remains `"1.0.0"` in v2.0. No schema change is needed.

### Optional dependencies

The `[prometheus]`, `[jupyter]`, `[fastapi]`, `[django]` extras
introduced in v1.6–v1.8 are stable and supported.

## If you pinned internal APIs

If your code reaches into any of these internals, you may need to
adjust:

| Internal | v1.x → v2.0 | Notes |
|---|---|---|
| `sentinel.cli._cmd_*` functions | unchanged | Still internal; do not call from outside. |
| `sentinel.storage.sqlite.SQLiteStorage._connection()` | unchanged | Still internal. |
| `_HAS_LANGCHAIN`, `_HAS_STARLETTE` module flags | unchanged | Still internal; test-only usage. |

None of these are listed as STABLE — they're implementation detail.
If you depend on them, consider filing an issue describing the use
case so we can promote the useful parts to a STABLE API.

## New capabilities to know about

### Trace integrity verification (v1.7+)

```python
result = sentinel.verify_integrity(trace_id)
if not result.verified:
    print(f"TAMPERED: {result.detail}")
```

Or via CLI:

```bash
sentinel verify --all
```

### Retention purge (v1.7+)

```bash
sentinel purge --before 2024-01-01 --dry-run   # preview
sentinel purge --before 2024-01-01 --yes       # actually delete
```

### Unified compliance check (v1.9+)

```bash
sentinel compliance check --all-frameworks --html --output full.html
```

Runs EU AI Act + DORA + NIS2 in one command.

### Prometheus textfile exporter (v1.6+)

```python
from sentinel.integrations.prometheus import PrometheusExporter

exporter = PrometheusExporter(
    sentinel=my_sentinel,
    output_path="/var/lib/prometheus/sentinel.prom",
    interval_seconds=15,
)
exporter.start()
```

The Grafana dashboard in `demo/grafana/dashboards/` will pick up
these metrics via node-exporter's textfile collector.

### FastAPI / Django middleware (v1.8+)

```python
# FastAPI
from sentinel.integrations.fastapi import SentinelMiddleware
app.add_middleware(SentinelMiddleware, sentinel=my_sentinel)

# Django — in settings.py
SENTINEL = Sentinel(project="myapp")
MIDDLEWARE = [..., "sentinel.integrations.django.SentinelMiddleware"]
```

## No deprecations

v2.0 deprecates nothing. Every v1.x API is intact.

## Smoke test before upgrading production

```bash
pip3 install sentinel-kernel==2.0.0 --dry-run
pytest                                     # your existing suite
python examples/smoke_test.py              # if you vendor it
sentinel demo                              # end-to-end sanity check
sentinel compliance check --all-frameworks # make sure your manifesto still passes
```
