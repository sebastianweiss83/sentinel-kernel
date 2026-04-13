# CI/CD integration

Sentinel is designed to fit into an existing pipeline, not to replace
it. Every check runs locally, in-process, with zero network calls and
no external services.

## The one-liner

```bash
pip install sentinel-kernel
sentinel ci-check
```

`sentinel ci-check` runs the Sentinel check bundle in-process and
returns a single aggregate exit code. It wraps three existing
checks:

1. **EU AI Act snapshot** — `EUAIActChecker` evaluates a default
   Sentinel instance against Art. 9, 12, 13, 14, 17. Fails only if a
   core logging article (12, 13, 14) is `NON_COMPLIANT`.
2. **Runtime sovereignty scan** — `RuntimeScanner` inspects every
   installed package. Fails on any critical-path sovereignty
   violation (a US-owned dependency reachable from
   `sentinel.core.tracer`, `sentinel.core.trace`, `sentinel.policy.*`,
   or `sentinel.storage.*`).
3. **Manifesto check** — `SentinelManifesto.check()` verifies your
   declared sovereignty posture. Skipped unless `--manifesto` is
   passed.

Exit codes:

- `0` — PASS or PARTIAL (some checks skipped, no failures)
- `1` — any check failed
- `2` — invalid `--manifesto` reference

## GitHub Actions

```yaml
name: Sentinel
on: [push, pull_request]
jobs:
  sentinel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install sentinel-kernel
      - run: sentinel ci-check --manifesto manifesto.py:MyManifesto
```

Add `--json` if you want to archive the result as an artifact:

```yaml
      - run: sentinel ci-check --json > sentinel-ci.json
      - uses: actions/upload-artifact@v4
        with:
          name: sentinel-ci-report
          path: sentinel-ci.json
```

## GitLab CI

```yaml
sentinel:
  image: python:3.12-slim
  script:
    - pip install sentinel-kernel
    - sentinel ci-check --manifesto manifesto.py:MyManifesto
  artifacts:
    when: always
    paths:
      - sentinel-ci.json
    expire_in: 30 days
```

## Pre-commit hook

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: sentinel-ci-check
        name: Sentinel CI check
        entry: sentinel ci-check
        language: system
        pass_filenames: false
        always_run: true
```

## Jenkins (declarative pipeline)

```groovy
stage('Sentinel') {
  steps {
    sh 'pip install sentinel-kernel'
    sh 'sentinel ci-check --json > sentinel-ci.json'
  }
  post {
    always {
      archiveArtifacts artifacts: 'sentinel-ci.json', allowEmptyArchive: true
    }
  }
}
```

## Running checks independently

`ci-check` is a thin aggregator. You can run each underlying check
on its own if you prefer finer-grained CI jobs:

```bash
sentinel scan --all            # sovereignty scanner
sentinel compliance check      # EU AI Act (and DORA/NIS2 with flags)
sentinel manifesto check manifesto.py:MyManifesto
```

Combine them yourself, or let `sentinel ci-check` do it for you.

## Air-gapped environments

Every check is in-process and offline:

- No network calls.
- No package registry lookups at runtime (the sovereignty scanner
  reads a bundled knowledge base).
- No external compliance service.
- No telemetry.

The same command works inside a classified network, behind an
air-gapped DMZ, and on a build agent with no internet egress.

## Quarterly evidence pack for auditors

`sentinel ci-check` gives you a CI gate. `sentinel evidence-pack`
gives you the paper artefact an auditor asks for.

```bash
pip install sentinel-kernel[pdf]

sentinel evidence-pack \
  --since 2026-01-01T00:00:00+00:00 \
  --until 2026-04-01T00:00:00+00:00 \
  --db /var/lib/sentinel/traces.db \
  --project procurement-agent \
  --financial-sector \
  --critical-infrastructure \
  --manifesto manifesto.py:MyManifesto \
  --output audit-2026-q1.pdf
```

What the pack contains:

1. Cover page with project, sovereign scope, data residency, storage
   backend, window, generation timestamp, and a scope reminder.
2. Executive summary — traces in window, ALLOW / DENY /
   EXCEPTION_REQUIRED counts, human overrides, unique agents, unique
   policies.
3. **EU AI Act coverage** (Art. 9 / 12 / 13 / 14 / 17), same output
   as `sentinel compliance check`.
4. **DORA coverage** (optional, `--financial-sector`).
5. **NIS2 coverage** (optional, `--critical-infrastructure`).
6. Trace samples — first and last up to 10 traces in the window.
7. **Hash manifest** — SHA-256 per-trace hashes plus a single
   **pack digest** over the whole list, so the document is tamper-
   evident against the NDJSON export of the same window.
8. **Sovereign attestation appendix** — `generate_attestation`
   output (self-contained, offline-verifiable with
   `sentinel attestation verify`).
9. **Dependency sovereignty scan** — total packages, sovereignty
   score, and any critical-path violations.

All data is pulled from the same public APIs the CI check uses.
No network calls, no external services, air-gapped capable. The
optional `[pdf]` extra installs `reportlab` (BSD-3-Clause,
UK-based, pure Python).

`evidence-pack` is not a substitute for audit work. It is a
reproducible technical artefact that the audit lead attaches as
evidence to the articles Sentinel automates. Everything above the
layer — risk management plan, technical documentation, conformity
assessment — is still the organisation's job.

## Scope reminder

`sentinel ci-check` gives you evidence that the technical controls
Sentinel is responsible for are in place. It does not discharge
organisational obligations — risk management, technical documentation,
conformity assessment, or post-market monitoring — that sit above the
kernel layer. See [eu-ai-act.md](eu-ai-act.md) for the full scope.
