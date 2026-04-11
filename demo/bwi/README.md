# Sentinel — BWI Evaluation Package

Everything BWI needs to evaluate Sentinel as a sovereign decision
record layer for federal AI deployments.

---

## 1. What Sentinel does

Sentinel wraps the execution of any AI agent and produces an
append-only, tamper-resistant record of every decision. The record
carries the agent name, the model identity, the policy that was
evaluated, the result, a SHA-256 hash of the inputs, and a
sovereignty assertion (jurisdiction + data residency). The record
is written before the agent call returns.

Sentinel is middleware. It does not replace your LLM, your agent
framework, or your storage. It wraps them so that the evidence of
what was decided remains inside your jurisdiction and your
control.

---

## 2. EU AI Act compliance status

| Article | Requirement                             | Automated | Status       |
|---------|-----------------------------------------|-----------|--------------|
| Art. 9  | Risk management                         | Partial   | PARTIAL      |
| Art. 10 | Data governance                         | No        | Organisational |
| Art. 11 | Technical documentation                 | No        | Organisational |
| Art. 12 | Automatic logging                       | Yes       | COMPLIANT    |
| Art. 13 | Transparency to deployers               | Yes       | COMPLIANT    |
| Art. 14 | Human oversight (kill switch)           | Yes       | COMPLIANT    |
| Art. 15 | Accuracy, robustness, cybersecurity     | No        | Organisational |
| Art. 17 | Quality management (traceability)       | Yes       | COMPLIANT    |

Automated coverage is verified by `sentinel compliance check` on
every PR in CI. See `compliance_report.py` for a BWI-specific run.

---

## 3. BSI IT-Grundschutz path

| Milestone                                     | Target       |
|-----------------------------------------------|--------------|
| v0.9 — Sovereignty platform (scanner, manifesto, compliance checker) | Now (shipped) |
| v1.0 — BSI pre-engagement contact             | Q2 2026      |
| v1.0 — IT-Grundschutz profile document review | Q3 2026      |
| v1.0 — Formal assessment submission           | Q4 2026      |
| v1.1 — VS-NfD classified profile              | Q1 2027      |

See `docs/bsi-profile.md` for the current mapping of Sentinel
components to IT-Grundschutz modules.

---

## 4. VS-NfD readiness

Sentinel's critical path:

- Contains **zero US-owned components** (verified by CI sovereignty check).
- Runs with **zero network connectivity** (verified by `tests/test_airgap.py`).
- Uses **only open standards** for trace export (NDJSON, OTel OTLP).

Remaining gaps for VS-NfD classification:

- Formal BSI assessment (planned v1.0).
- Cryptographic tamper-detection on trace records (SHA-256 hashes are
  present today; a signed-log mode is tracked for a post-v1.0
  release).
- Hardened deployment profile with signed binaries.

---

## 5. Running the demo

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,otel]"
python demo/bwi/compliance_report.py
```

This produces `bwi_compliance_report.html` — a single self-contained
HTML file suitable for BWI review.

For the full stack with Grafana, Prometheus, and LangFuse:

```bash
cd demo
docker compose up --build
```

Grafana: http://localhost:3001 (admin / sentinel)
LangFuse: http://localhost:3000
Prometheus: http://localhost:9090

---

## 6. Air-gapped deployment guide

Sentinel supports three storage backends:

| Backend            | Use case                                   |
|--------------------|--------------------------------------------|
| `SQLiteStorage`    | Single-node, on-premise                    |
| `PostgresStorage`  | Multi-node, shared on-premise infrastructure |
| `FilesystemStorage`| Classified / air-gapped, NDJSON files      |

For air-gapped deployments, use `FilesystemStorage` with a
pre-populated mirror of your policy files. No PyPI access, no
language model API, no OTel collector is required. The CI job
`airgap` in `.github/workflows/ci.yml` validates this on every push.

---

## 7. Infrastructure requirements

Minimum:

- Python 3.11 or 3.12 runtime (sovereign Linux distribution)
- 1 CPU core, 256 MB RAM, 1 GB disk (for SQLite storage)

Recommended for federal deployment:

- PostgreSQL cluster on BWI-managed infrastructure
- Grafana + Prometheus + OpenTelemetry Collector on BWI-managed infrastructure
- No external network egress required

---

## 8. Integration with BWI's existing sovereign infrastructure

Sentinel is deliberately minimal. Integration points:

- **Storage** — drop-in `StorageBackend` implementations for BWI's
  sovereign database services (we provide SQLite, PostgreSQL, and
  filesystem; a custom backend is a single class implementing four
  methods).
- **Observability** — OpenTelemetry OTLP/gRPC to any collector on
  BWI-managed infrastructure. No vendor lock-in.
- **Policy** — OPA Rego policies can be versioned and reviewed like
  code. `LocalRegoEvaluator` runs OPA in-process, no server.
- **Identity** — traces carry agent and model identifiers; wire up
  to your existing identity system by passing them through.

---

## 9. Support and governance

- **License:** Apache 2.0, permanently. No relicensing path, no CLA
  that grants copyright, no enterprise edition.
- **Governance:** Targeting Linux Foundation Europe stewardship
  with v1.0 (Q4 2026).
- **Incidents:** `SECURITY.md` in the repository root.
- **Upstream contact:** sebastian@swentures.com

---

## 10. Next steps (design partner proposal)

Sentinel is looking for one to three design partners in the EU
regulated sector for a structured 12-week evaluation programme:

- Week 1–2: technical discovery (your current architecture, constraints)
- Week 3–6: pilot integration (one wrapped agent, local storage)
- Week 7–9: sovereignty scan + manifesto definition (together)
- Week 10–12: BSI pre-engagement preparation

Output: a signed-off sovereignty posture document for your
deployment and an upstream PR to Sentinel with any integration
points you needed.

Contact sebastian@swentures.com to discuss.
