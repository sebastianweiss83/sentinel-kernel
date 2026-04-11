# Real-world examples

Five realistic industry scenarios. Each is generic by design: every
regulated organisation sees their own situation in one of them. No
named customers, no proprietary details. Every example maps to
runnable code in [`examples/`](../examples/) or [`examples/policies/`](../examples/policies/).

---

## 1. Defence and aerospace — autonomous go / no-go

**The situation.** An autonomous system evaluates mission parameters
and produces a go / no-go decision. A human operator must be able to
halt all decisions at any time (EU AI Act Art. 14). Every decision
must be reproducible years after the fact for accident investigation
and formal audit. The deployment is air-gapped.

**What Sentinel provides.**

- `FilesystemStorage` writes decision records to NDJSON on local disk.
  No network. Works under VS-NfD / SECRET classification constraints.
- `SimpleRuleEvaluator` (or `LocalRegoEvaluator` for Rego policies)
  runs safety checks in-process before the mission logic executes.
- `sentinel.engage_kill_switch("operator halted — see incident log")`
  halts all decisions without restart. Every blocked attempt is
  recorded as a DENY trace with a `HumanOverride` entry.
- `RuntimeScanner` proves there are no US-owned packages in the
  critical path — CI-enforced on every PR.

**Runnable example.** [`examples/05_kill_switch.py`](../examples/05_kill_switch.py)
and [`examples/06_filesystem_storage.py`](../examples/06_filesystem_storage.py).

**Reference policy.** [`examples/policies/mission_safety.rego`](../examples/policies/mission_safety.rego).

---

## 2. Healthcare — treatment recommendation with escalation

**The situation.** An AI system recommends a treatment plan. For
low-risk cases the recommendation goes to the treating clinician
directly; for high-risk cases a second opinion must be obtained
before the recommendation is presented. Patient data must remain
on-premise (GDPR + national healthcare data laws). Every
recommendation must be auditable and linked to the clinician who
actioned it.

**What Sentinel provides.**

- `DataResidency.EU_DE` (or equivalent) on every trace — machine
  evidence of where the data was processed.
- Rego policy evaluates `risk_score`, `patient_age`, and
  `previous_adverse_events` and routes low-risk to `ALLOW`,
  medium-risk to `EXCEPTION_REQUIRED` (escalate), high-risk to
  `DENY` (never bypass the human).
- Clinician sign-off is recorded as a `HumanOverride` linked to
  the original trace by `parent_trace_id` — the decision record
  is append-only.
- `inputs_hash` is SHA-256 by default; raw PII never appears in
  the trace unless explicitly opted in. Regulator asks "was patient
  X's data processed?" and the answer is reproducible without
  exposing the data itself.

**Runnable example.** [`examples/03_policy_simple_rule.py`](../examples/03_policy_simple_rule.py)
demonstrates the escalation pattern.

**Reference policy.** [`examples/policies/medical_escalation.rego`](../examples/policies/medical_escalation.rego).

---

## 3. Financial services — transaction approval with velocity checks

**The situation.** An automated system approves (or rejects)
individual financial transactions against fraud rules, sanctions
lists, and per-customer velocity limits. Regulatory regimes such
as DORA require a tamper-resistant incident and decision record
retained for several years. Any third-party processor with US
jurisdiction creates CLOUD Act exposure on the evidence record.

**What Sentinel provides.**

- `PostgresStorage` (append-only) for the decision record.
  Deployed on-premise or in an EU-sovereign database service.
- Policy evaluates `amount`, `velocity_last_hour`,
  `sanctions_score`, and `customer_risk_tier`. Every DENY is
  recorded with the name of the triggering rule.
- `OTelExporter` streams span attributes `sentinel.sovereign_scope`
  and `sentinel.data_residency` to the existing APM stack — the
  same dashboards the SRE team already uses now show sovereignty
  posture alongside latency.
- `EUAIActChecker` runs in CI and prevents regressions: if
  anyone removes the kill switch or disables the policy evaluator,
  the `compliance check` job fails the PR.

**Runnable example.** [`examples/13_full_pipeline.py`](../examples/13_full_pipeline.py).

**Reference policy.** [`examples/policies/financial_transaction.rego`](../examples/policies/financial_transaction.rego).

---

## 4. Public administration — decisions with transparency obligations

**The situation.** A public body uses an AI system to triage citizen
requests. Law requires that any individual can ask for the reasoning
behind a decision about them, and that the system operator can
identify the policy version in force at the time. Procurement rules
forbid single-vendor lock-in.

**What Sentinel provides.**

- Every trace records `agent`, `agent_version`, `model`,
  `model_version`, `policy`, `policy_version`, `policy_result`,
  `policy_rule`. A human-readable reconstruction is a single query.
- `StorageBackend` is an interface with three ready-made
  implementations (SQLite, PostgreSQL, filesystem NDJSON) and any
  new backend is 4 methods. No lock-in.
- NDJSON export gives a portable archive format that survives
  any future migration.
- Apache 2.0, permanently. No CLA, no enterprise edition, no
  relicensing path.

**Runnable example.** [`examples/07_postgresql_storage.py`](../examples/07_postgresql_storage.py)
(on-premise deployment) and [`examples/06_filesystem_storage.py`](../examples/06_filesystem_storage.py)
(NDJSON archive).

**Reference policy.** [`examples/policies/access_control.rego`](../examples/policies/access_control.rego).

---

## 5. Enterprise procurement — high-volume approval with delegation

**The situation.** A large organisation runs thousands of
procurement approvals per day. Approval authority is delegated by
amount, cost centre, and approver level. Every override by a human
must be recorded with the justification. The finance team needs a
monthly report showing who approved what and under which policy.

**What Sentinel provides.**

- `@sentinel.trace` wraps the approval function. Zero changes to
  the existing approval logic.
- `SimpleRuleEvaluator` encodes the delegation matrix as Python.
- Human overrides of a DENY become new linked traces — the
  original DENY is never mutated. An auditor can see both the
  automated decision and the documented human reasoning.
- `sentinel.query(policy_result=PolicyResult.DENY, limit=10000)`
  is the monthly report. Exported to CSV or NDJSON for
  finance tooling.

**Runnable example.** [`examples/03_policy_simple_rule.py`](../examples/03_policy_simple_rule.py)
shows the pattern with sample data. Scale up by wiring to
your real approval service.

**Reference policy.** [`examples/policies/procurement_approval.rego`](../examples/policies/procurement_approval.rego).

---

## How to adapt these

Each scenario maps to real Sentinel primitives that already exist:

| Primitive | Where it lives |
|---|---|
| `@sentinel.trace`         | `sentinel.core.tracer.Sentinel.trace` |
| `SimpleRuleEvaluator`     | `sentinel.policy.evaluator` |
| `LocalRegoEvaluator`      | `sentinel.policy.evaluator` (needs OPA binary) |
| `FilesystemStorage`       | `sentinel.storage.filesystem` |
| `PostgresStorage`         | `sentinel.storage.postgres` (optional extra) |
| `SentinelCallbackHandler` | `sentinel.integrations.langchain` (optional extra) |
| `OTelExporter`            | `sentinel.integrations.otel` (optional extra) |
| `EUAIActChecker`          | `sentinel.compliance.euaiact` |
| `SentinelManifesto`       | `sentinel.manifesto` |

There is no code in any of these scenarios that isn't shipped in
the public repository. Clone, read, adapt.
