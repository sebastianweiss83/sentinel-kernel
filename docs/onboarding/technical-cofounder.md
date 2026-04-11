# Technical Co-founder Onboarding

Welcome to `sentinel-kernel`. This document gets you from zero to
productive in one afternoon.

## The one-paragraph pitch

Sentinel is EU-sovereign AI decision middleware. You wrap any AI agent
with `@sentinel.trace`, we record a tamper-resistant decision trace to
local storage, you pass an EU AI Act Art. 12/13/14 audit. The three
invariants are: no US CLOUD Act exposure in the critical path, the
air-gapped path must always work, and Apache 2.0 permanently. The
sovereignty is the product.

## Architecture in 5 minutes

```
┌─────────────────────┐
│  Your AI agent      │   any Python callable, sync or async
└──────────┬──────────┘
           │ @sentinel.trace
┌──────────▼──────────┐
│  Tracer (interceptor)  │   wraps the call, captures in/out
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Policy evaluator     │   SimpleRule | LocalRego | custom
└──────────┬──────────┘   → ALLOW / DENY / EXCEPTION
           │
┌──────────▼──────────┐
│  DecisionTrace (data) │   frozen dataclass, schema-versioned
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Storage backend      │   SQLite | PostgreSQL | Filesystem
└──────────┬──────────┘   append-only, local-first
           │
┌──────────▼──────────┐
│  Optional exporters   │   OTel, LangFuse, LangChain
└─────────────────────┘   all additive — never in critical path
```

Five layers, each a clean interface. Storage always happens first.
Exporters run after the trace is durable locally. A broken OTel
collector cannot drop a trace.

## The three invariants

1. **Local storage first.** Any feature must work with `SQLiteStorage`
   or `FilesystemStorage` alone. OTel/LangFuse/Postgres are additive.
2. **No US-owned dependency in the critical path.** The CI/CD
   sovereignty scanner flags every new dependency. If a package is
   US-incorporated and makes network calls at runtime, it cannot live
   in `sentinel/`. It can live in an optional extras group guarded by
   `ImportError`.
3. **Air-gap must always pass.** `tests/test_airgap.py` installs a
   network-denying socket shim and runs the full critical path. If
   any new code reaches the network unconditionally, CI goes red.

## Development setup

```bash
git clone git@github.com:sebastianweiss83/sentinel-kernel.git
cd sentinel-kernel
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -q                    # expect 306+ passing, 96%+ coverage
python examples/smoke_test.py       # expect 40/40
sentinel demo                       # expect exit 0 + sovereignty_report.html
```

## Key files to read first — in this order

1. **`CLAUDE.md`** — current version, test count, coverage, open issues.
   Auto-generated. Ground truth for session continuity.
2. **`sentinel/core/tracer.py`** — the `Sentinel` class itself. The
   `@sentinel.trace` decorator, kill switch, storage routing.
3. **`sentinel/core/trace.py`** — the `DecisionTrace` dataclass. All
   mandatory fields, immutability, schema versioning, serialisation.
4. **`sentinel/policy/evaluator.py`** — how policies are evaluated.
   `SimpleRuleEvaluator` + `LocalRegoEvaluator`.
5. **`tests/test_airgap.py`** — the sovereignty invariants enforced
   by CI. Read this before adding any dependency.
6. **`docs/rfcs/RFC-001-sovereignty-manifest.md`** — the portable
   manifesto spec. Language-agnostic.
7. **`docs/bsi-profile.md`** — BSI IT-Grundschutz mapping. What we
   automate, what the operator must do.

## How to add a new integration

Integrations live in `sentinel/integrations/`. Follow the LangChain
integration as reference:

1. **Sovereignty check.** Document in the PR:
   - Parent company + jurisdiction
   - CLOUD Act exposure
   - Runtime network calls
   - Air-gap compatibility

2. **Create the module.** Put it in `sentinel/integrations/<name>.py`.

3. **Guard the imports.** At module top:
   ```python
   try:
       import langchain  # or whatever
   except ImportError as exc:
       raise ImportError(
           "Install with: pip3 install sentinel-kernel[langchain]"
       ) from exc
   ```

4. **Expose a callback or adapter class.** Record a trace on every
   framework event you care about. Set `sovereign_scope` and
   `data_residency` from the Sentinel instance, never hardcode.

5. **Add the optional extra.** In `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   langchain = ["langchain>=0.1"]
   ```

6. **Write the five mandatory tests.** See
   `tests/test_integration_langchain.py`:
   - happy path
   - offline mode
   - policy DENY recorded
   - missing-dep raises helpful `ImportError`
   - sovereignty metadata flows through

## How to add a new storage backend

Implement `sentinel.storage.base.StorageBackend`. The four methods
are `initialise`, `save`, `query`, `get`. Read
`sentinel/storage/filesystem.py` as the reference implementation.

Mandatory invariants:

- **Append-only.** No `UPDATE`, no `DELETE`. Corrections are new
  traces linked via `parent_trace_id`.
- **Deterministic output.** `save` must never reorder fields.
- **Network-free by default.** If your backend calls out (PostgreSQL
  across TLS, S3, etc.) document that in the class docstring and
  ensure it is usable offline for dev.

Write storage-agnostic tests that parametrise across all backends —
see `tests/test_storage_*.py`.

## Release process

Three commands. Full details in `docs/releasing.md`.

```bash
git tag v1.2.0 && git push origin v1.2.0
```

CI builds the sdist/wheel and publishes to PyPI via OIDC trusted
publisher. No API tokens involved.

## Architecture Decision Records

- [ADR-001](../architecture-decision-records/ADR-001-local-first.md) — Why local storage is the reference
- [ADR-002](../architecture-decision-records/ADR-002-apache2-permanent.md) — Why Apache 2.0 is permanent
- [ADR-003](../architecture-decision-records/ADR-003-schema-versioning.md) — Schema versioning for DecisionTrace

Add a new ADR before any architectural change.
