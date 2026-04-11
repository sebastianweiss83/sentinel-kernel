# EU AI Act Art. 12/13/14 mapping for BSI review

This document maps Sentinel features to the specific EU AI Act
article requirements that a BSI IT-Grundschutz assessment needs
to confirm.

## Art. 12 — Record-keeping

### Requirement text (summarised)

High-risk AI systems must technically allow **automatic recording**
of events ("logs") throughout the lifetime of the system. Logs
must enable the identification of situations that may lead to
substantial modification or present risks, as well as facilitate
post-market monitoring.

### Sentinel coverage

| Sub-requirement | How Sentinel addresses it | Evidence |
|---|---|---|
| **Automatic logging** | `@sentinel.trace` decorator wraps any agent function; every call produces a trace without operator action | `sentinel/core/tracer.py:trace` |
| **Throughout the lifetime** | Storage is append-only; retention is operator-configurable; `purge_before` has safe dry-run | `sentinel/storage/base.py:purge_before` |
| **Events enabling identification** | Every trace carries: agent, model, policy_id, policy_result, rule_triggered, inputs_hash, output_hash, latency_ms, sovereign_scope, data_residency, schema_version | `sentinel/core/trace.py:DecisionTrace` |
| **Post-market monitoring** | `sentinel.query()` supports filters by project, agent, policy_result, time range | `sentinel/core/tracer.py:query` |
| **Tamper-resistance** | SHA-256 hashing on every input and output; `verify_integrity()` recomputes and compares | `sentinel/core/tracer.py:verify_integrity` |

### Automated check

```bash
sentinel compliance check --json
```

Returns `"Art. 12": {"status": "COMPLIANT"}` when a storage backend
is configured.

## Art. 13 — Transparency and information provision

### Requirement text (summarised)

High-risk AI systems must be designed so that users can interpret
the output and use it appropriately. Providers must supply
documentation covering capabilities, limitations, and the level
of accuracy expected.

### Sentinel coverage

| Sub-requirement | How Sentinel addresses it | Evidence |
|---|---|---|
| **Model identification** | `DecisionTrace.model_name`, `model_provider`, `model_version` | `sentinel/core/trace.py` |
| **Policy identification** | `PolicyEvaluation.policy_id`, `policy_version`, `rule_triggered` | `sentinel/core/trace.py` |
| **Decision rationale** | `PolicyEvaluation.rationale` (free text; evaluator-specific) | `sentinel/policy/evaluator.py` |
| **Data residency assertion** | `DecisionTrace.data_residency` + `sovereign_scope` on every trace | `sentinel/core/trace.py` |

### Automated check

```bash
sentinel compliance check
```

Returns `"Art. 13": {"status": "COMPLIANT"}` when traces carry the
required metadata fields.

## Art. 14 — Human oversight

### Requirement text (summarised)

High-risk AI systems must be designed so that natural persons can
effectively oversee their operation. The oversight must include
the ability to **stop the system** through a button or similar
mechanism.

### Sentinel coverage

| Sub-requirement | How Sentinel addresses it | Evidence |
|---|---|---|
| **Kill switch** | `Sentinel.engage_kill_switch(reason)` halts all subsequent agent calls immediately. Thread-safe, no restart required. | `sentinel/core/tracer.py:engage_kill_switch` |
| **Override mechanism** | `HumanOverride` dataclass; every override creates a linked trace with the original intact | `sentinel/core/trace.py:HumanOverride` |
| **Auditability of oversight** | Blocked calls after `engage_kill_switch` produce a DENY trace with `rule_triggered="kill_switch"` and the reason string | `sentinel/core/tracer.py:_execute_traced` |
| **Disengagement audit** | `disengage_kill_switch(reason)` also requires a reason | `sentinel/core/tracer.py:disengage_kill_switch` |

### Automated check

```bash
sentinel compliance check
```

Returns `"Art. 14": {"status": "COMPLIANT"}` when the kill switch
API is present (which it always is for `Sentinel` instances).

## Coverage table summary

| Article | Sentinel status | Automatable? |
|---|---|---|
| Art. 9  — Risk management | PARTIAL | Depends on policy evaluator configuration |
| Art. 10 — Data governance | ACTION_REQUIRED | Organisational process |
| Art. 12 — Record-keeping | COMPLIANT | Yes |
| Art. 13 — Transparency | COMPLIANT | Yes |
| Art. 14 — Human oversight | COMPLIANT | Yes |
| Art. 15 — Accuracy / robustness | ACTION_REQUIRED | Organisational process |
| Art. 17 — Quality management | PARTIAL | Needs CI integration |

Generate the current status with:

```bash
sentinel compliance check --html --output eu-ai-act.html
```

## For BSI reviewers

Each COMPLIANT / PARTIAL status is backed by:

1. A dedicated test file (see `docs/bsi-pre-engagement/test-evidence.md`).
2. A specific file and line in `sentinel/` that implements the
   behaviour (linked in the Sentinel coverage tables above).
3. A machine-readable trace emitted on every decision that
   carries the evidence fields.

We welcome review of any of these.
