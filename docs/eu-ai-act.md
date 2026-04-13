# EU AI Act — Sentinel compliance mapping

Regulation (EU) 2024/1689 entered into force 1 August 2024.

**Annex III enforcement date: 2 August 2026.**
Annex I (medical devices, machinery) enforcement: 2 August 2027.

Penalties for non-compliant high-risk AI: up to **€15M or 3% of global annual turnover**.

Extra-territorial scope: applies to any organisation serving EU users regardless of headquarters location.

## Scope of this layer — read first

Sentinel addresses the technical requirements of Art. 9, 12, 13, 14, and 17. It does not address Art. 10 (data governance), Art. 11 (technical documentation), or Art. 15 (accuracy and robustness) — those require organisation-level action beyond what a middleware kernel can provide.

Whether a specific AI system is classified as high-risk under Annex III depends on its use case. Sentinel does not make that classification. Consult legal counsel to determine your obligations.

Sentinel is the decision trace and policy enforcement layer. It is not a full EU AI Act compliance solution, and no middleware kernel can be. It gives you the technical evidence, enforcement, and oversight hooks that the organisational process above it needs.

## Article mapping

### Art. 9 — Risk management

Requires documented, ongoing risk assessment for high-risk AI systems.

Sentinel records the policy name, version, and result in every trace. Any decision that triggered a DENY rule is queryable. Risk posture is continuously documented through the trace record.

### Art. 12(1) — Automatic logging over the system's lifetime

Requires automatic logging of all events throughout the operational lifetime of the system.

Every call wrapped by `@sentinel.trace` produces a trace entry automatically. No manual step. No opt-in. Traces are written before the agent call returns.

### Art. 12(2) — Logs enable identification of risk situations

Logs must be structured to enable identification and analysis of risk situations.

Sentinel traces are structured JSON, schema-versioned, queryable by `policy_result`, `policy_rule`, `agent`, `model`, and `timestamp`. Every DENY includes the name of the rule that triggered it.

### Art. 13 — Transparency to deployers

Deployers must be able to understand the system's capabilities, limitations, and performance.

Every trace records: agent name and version, model identifier and version, policy name and version, and the outcome. A deployer can reconstruct exactly what was decided, by which system, under which policy, at any point in the system's history.

### Art. 14 — Human oversight

High-risk AI systems must be designed to allow human oversight, including the ability to interrupt or override.

Sentinel's override mechanism records any human intervention as a separate trace entry linked to the original by `parent_trace_id`. The original is never modified. Human overrides are permanently recorded with `override_by`, `override_reason`, and `override_at`.

Kill switch implementation: a policy that returns DENY for all inputs can be loaded at runtime without restart. This is the Art. 14 halt mechanism.

### Art. 17 — Quality management

Providers must implement a quality management system including traceability.

Sentinel produces a continuous, tamper-resistant, append-only record of system behaviour. Every trace includes a schema version, enabling reconstruction of historical system state against the exact policy in force at that time.

