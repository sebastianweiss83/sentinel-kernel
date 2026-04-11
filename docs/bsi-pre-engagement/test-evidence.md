# Test evidence (BSI pre-engagement)

BSI IT-Grundschutz `APP.6.A3` (secure software development)
requires evidence that the software has been tested systematically.
Sentinel's test suite is that evidence.

## Numbers

- **Tests:** 503+ (grows per release)
- **Line coverage:** **100%** on every module in `sentinel/`
- **Smoke test:** 40 steps, runs on every release
- **Air-gap tests:** 11, runs on every PR

Coverage is enforced in CI with `--cov-fail-under=75` as a floor;
the actual measurement is 100%.

## Test categories

### Unit tests

- `tests/test_decorator_contract.py` — the `@sentinel.trace`
  contract (async/sync, args/kwargs, return values, exceptions).
- `tests/test_trace.py` — `DecisionTrace` mandatory field checks,
  schema-version stability, hash computation.
- `tests/test_policy_evaluator.py` — `SimpleRuleEvaluator`,
  `LocalRegoEvaluator`, `NullPolicyEvaluator` behaviours.
- `tests/test_policy_version.py` — `PolicyVersion` dataclass.
- `tests/test_manifesto.py` — all requirement types.
- `tests/test_scanner.py` — runtime / CI/CD / infrastructure scanners.

### Integration tests

- `tests/test_integration_langchain.py` — LangChain callback
  handler, offline mode, DENY recording, missing-dep error.
- `tests/test_integration_haystack.py` — Haystack component
  end-of-run recording with a mocked Haystack module.
- `tests/test_integration_otel.py` — OTel span emission via a
  fake tracer, with wrapper delegation and error paths.
- `tests/test_integration_langfuse.py` — LangFuse enrichment.
- `tests/test_integration_prometheus.py` — Prometheus textfile
  exporter, including background thread lifecycle.
- `tests/test_integration_jupyter_fastapi_django.py` — Jupyter
  widget, FastAPI middleware with TestClient, Django middleware
  with configured settings.

### Compliance tests

- `tests/test_eu_ai_act_fields.py` — every EU AI Act mandatory
  field is present on every trace.
- `tests/test_compliance_dora_nis2.py` — DORA and NIS2 checkers.
- `tests/test_rfc001_compliance.py` — validates a real manifesto
  against the RFC-001 schema.

### Air-gap tests — **the sovereignty evidence**

`tests/test_airgap.py` installs a socket shim that raises on every
network call attempt (`socket.socket()`), then runs the full
`@sentinel.trace` critical path with a policy evaluator, storage
write, and query. The tests cover:

1. SQLite storage offline
2. Filesystem storage offline
3. Policy evaluation offline (SimpleRule)
4. Kill switch offline
5. Override offline
6. Query offline
7. Export NDJSON offline
8. Import NDJSON offline
9. Scanner offline
10. Compliance checker offline
11. HTML report generation offline

A single failure in this file is a deployment blocker for any
VS-NfD or air-gapped use case.

## How to reproduce for an auditor

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/ -v                               # 503+ tests
pytest tests/test_airgap.py -v                 # 11 sovereignty invariants
pytest tests/ --cov=sentinel --cov-report=term # 100% coverage
python scripts/check_sovereignty.py            # runtime scanner
python examples/smoke_test.py                  # 40-step validation
```

## CI discipline

Every commit to `main` triggers the full test matrix on Python
3.11 and 3.12. The matrix includes:

- `test` — pytest with coverage
- `sovereignty-check` — CLOUD Act deny script + EU AI Act field check
- `lint` — ruff + mypy strict
- `quickstart` — smoke tests with examples
- `airgap` — network-denied critical-path run
- `update-claude-md` — auto-refresh the state block on green pushes

The release job publishes via OIDC trusted publisher to PyPI with
no long-lived tokens.
