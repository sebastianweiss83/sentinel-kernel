# EU AI Act Compliance Mapping

**Regulation:** EU 2024/1689 — Artificial Intelligence Act
**Entered into force:** 1 August 2024
**Annex III high-risk enforcement date:** **2 August 2026**

This document maps relevant EU AI Act articles to specific Sentinel
trace fields and mechanisms that address each requirement.

---

## Regulation overview

The EU AI Act (Regulation EU 2024/1689) establishes a risk-based framework
for AI systems deployed in the European Union. It was published in the
Official Journal on 12 July 2024 and entered into force on 1 August 2024.

Key compliance dates:

| Date | What applies |
|---|---|
| 2 February 2025 | Prohibited AI practices (Title II) |
| 2 August 2025 | GPAI model obligations (Chapter V) |
| **2 August 2026** | **Annex III high-risk AI systems (full obligations)** |
| 2 August 2027 | Annex I high-risk AI systems integrated into regulated products |

Sentinel is designed for organisations deploying **Annex III high-risk AI systems**,
where full compliance is required from **2 August 2026**.

---

## Penalties

Non-compliance with high-risk AI system obligations carries penalties of:

- Up to **€15 million** or **3% of global annual turnover** (whichever is higher)
  for violations of Articles 6–49
- Up to **€35 million** or **7% of global annual turnover** for prohibited practices
- Up to **€7.5 million** or **1.5% of global annual turnover** for supplying
  incorrect information to authorities

---

## Article-by-article mapping

### Article 9 — Risk management system

**Requirement:** Providers of high-risk AI systems shall establish, implement,
document and maintain a risk management system. The system shall be a continuous
iterative process planned and run throughout the entire lifecycle of the
high-risk AI system.

**How Sentinel addresses it:**

- Every agent decision is recorded with the policy evaluated and its result.
- Risk posture is queryable across all decisions: filter by `policy_result: DENY`
  or `policy_result: EXCEPTION_REQUIRED` to identify risk patterns.
- Policy version is recorded in every trace, enabling reconstruction of the
  risk management state at any historical point.
- The append-only trace log provides a continuous record throughout the
  system's operational lifetime.

**Relevant trace fields:** `policy`, `policy_version`, `policy_result`,
`policy_rule`, `timestamp`

---

### Article 12(1) — Automatic logging

**Requirement:** High-risk AI systems shall technically allow for the automatic
recording of events (logs) over the lifetime of the system.

**How Sentinel addresses it:**

- The `@sentinel.trace` decorator automatically records every agent decision
  without requiring changes to agent logic.
- Traces are produced for every call — there is no opt-out at the individual
  decision level once Sentinel is configured.
- Logging is automatic and cannot be bypassed by the agent implementation.

**Relevant trace fields:** `trace_id`, `timestamp`, `agent`, `agent_version`,
`model`, `model_version`, `inputs_hash`, `output`, `latency_ms`

---

### Article 12(2) — Log capabilities

**Requirement:** The logging capabilities shall ensure a level of traceability
of the AI system's functioning throughout its lifecycle that is appropriate to
the intended purpose of the system. They shall enable the monitoring of the
operation of the high-risk AI system, the identification of risk situations,
and facilitate post-market monitoring.

**How Sentinel addresses it:**

- Traces are structured and queryable by any field combination.
- Export as NDJSON enables integration with external monitoring and analytics tools.
- `policy_result` and `policy_rule` fields directly identify risk situations
  (denials, exceptions requiring human intervention).
- Full trace history is preserved for post-market monitoring and regulatory review.

**Relevant trace fields:** All mandatory fields, plus `parent_trace_id` for
decision chains and override tracking.

---

### Article 12(3) — Tamper resistance

**Requirement:** The logs shall be kept for a period that is appropriate in
the light of the intended purpose of the high-risk AI system and applicable
legal obligations.

**How Sentinel addresses it:**

- Traces are append-only. No trace can be modified or deleted after writing.
- Storage backends enforce immutability at the interface level.
- Override and correction semantics produce new linked entries rather than
  modifying existing records.
- NDJSON export enables long-term archival independent of the runtime system.

**Relevant mechanism:** Append-only storage constraint, `parent_trace_id`
linking, immutable `trace_id`.

---

### Article 13 — Transparency and provision of information to deployers

**Requirement:** High-risk AI systems shall be designed and developed in such
a way as to ensure that their operation is sufficiently transparent to enable
deployers to interpret the system's output and use it appropriately.

**How Sentinel addresses it:**

- Every trace records the model used, the policy evaluated, and the policy result.
- Deployers can query traces to understand exactly which policy governed each
  decision and what the model's contribution was.
- Policy version tracking enables deployers to see when policy changes affected
  decision outcomes.

**Relevant trace fields:** `model`, `model_version`, `policy`, `policy_version`,
`policy_result`, `policy_rule`, `output`

---

### Article 14 — Human oversight

**Requirement:** High-risk AI systems shall be designed and developed in such
a way, including with appropriate human-machine interface tools, that they can
be effectively overseen by natural persons during the period in which the AI
system is in use.

**How Sentinel addresses it:**

- The override mechanism enables humans to intervene in any policy decision.
- Overrides produce a second, linked trace entry preserving the identity of
  the overrider, the reason, and the timestamp.
- The original trace is never modified — the full decision chain (automated
  decision → human override) is permanently recorded.
- Override patterns can be queried to identify areas where human oversight
  is frequently exercised.

**Relevant trace fields:** `override_by`, `override_reason`, `override_at`,
`parent_trace_id`

---

### Article 17 — Quality management system

**Requirement:** Providers of high-risk AI systems shall put a quality
management system in place that ensures compliance with this Regulation.
That quality management system shall include strategies for traceability
of processes.

**How Sentinel addresses it:**

- The continuous, tamper-resistant trace log provides a complete record of
  system behaviour in production.
- Schema versioning ensures traces are always interpretable according to
  the version under which they were created.
- The append-only constraint ensures the quality record cannot be retroactively
  altered.
- Export capabilities enable integration with existing quality management
  systems and regulatory reporting workflows.

**Relevant mechanism:** Full trace schema, `schema_version`, append-only storage,
NDJSON export.

---

## Scoping note

**Sentinel does not determine whether your AI system is classified as high-risk.**

Whether a specific AI system falls under Annex III of the EU AI Act depends
on its use case, deployment context, and the sector in which it operates.
This is a legal determination that requires analysis by qualified legal counsel
familiar with your specific deployment.

Sentinel provides the technical infrastructure to satisfy logging, transparency,
human oversight, and quality management requirements **if** your system is
classified as high-risk. It is designed so that the cost of compliance is
adoption of the kernel — not a retrofit after a regulatory determination.

---

## Further reading

- [Full regulation text (EUR-Lex)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)
- [Annex III — High-risk AI systems](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689#d1e3832-1-1)
- [Decision trace schema reference](schema.md)
