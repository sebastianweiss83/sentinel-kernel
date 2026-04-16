# For compliance officers / DPOs

You own the audit trail. You answer the auditor. You need to know
exactly which EU AI Act obligations Sentinel covers, which it doesn't,
and what evidence you can hand to a regulator on day one of an
inspection.

## See the artefact before installing anything

- 📄 [Sample evidence pack (PDF)](../samples/audit-evidence-pack-sample.pdf)
  — self-contained, tamper-resistant, exactly the format your auditor
  receives.
- 📋 [Sample `audit-gap` score](../samples/audit-gap-output.txt) — honest
  split between what Sentinel closes, what your organisation must
  close, and what needs human authorship.

## What Sentinel covers

| Regulation | Article | Status | How |
|---|---|---|---|
| EU AI Act | Art. 12 (logging) | **Automated** | every traced call produces an append-only record with SHA-256 input/output hashes, policy result, timestamp, sovereignty scope |
| EU AI Act | Art. 13 (transparency to deployers) | **Automated** | agent, model, policy, and evaluator fields on every trace |
| EU AI Act | Art. 14 (human oversight) | **Automated** | runtime kill switch halts every decision in ≤1 ms, records the halt as a linked DENY trace |
| EU AI Act | Art. 17 (quality-management traceability) | **Automated** | schema-versioned immutable record, NDJSON export, portable |
| GDPR | Art. 25 (data protection by design) | **Automated** | hash-only storage by default — see [provability.md](../provability.md#privacy-by-default-v320) |
| GDPR | Art. 22 (right to explanation) | **Pattern** | explicit `store_outputs=True` opt-in documented in [explainability-art-22.md](../explainability-art-22.md) |
| DORA | Art. 10 / Art. 16 logging | **Automated** | trace store doubles as DORA incident logging substrate; [dora-compliance.md](../dora-compliance.md) |
| NIS2 | Art. 21 / Art. 23 | **Partial** | decision-side covered; sector-specific thresholds (BNetzA, etc.) are operator scope |

## What Sentinel does NOT cover (and this is explicit)

| Regulation | Article | Why not |
|---|---|---|
| EU AI Act | Art. 9 (risk management framework) | Organisational obligation — cannot be automated by a middleware layer |
| EU AI Act | Art. 10 (data governance documentation) | Human authorship required |
| EU AI Act | Art. 11 (Annex IV technical documentation) | Human authorship required |
| EU AI Act | Art. 15 (accuracy, robustness) | Operator defines the accuracy metrics; Sentinel only records whatever score is emitted |
| EU AI Act | Art. 16 (provider registration, CE marking) | Conformity-assessment process, not a trace artefact |
| EU AI Act | Art. 26 (deployer oversight procedures) | Operator procedural obligation |

Running `sentinel audit-gap` prints the exact split for *your* setup,
with which gaps the library can close (one command each) and which
require a human in a room.

## The first document you send to your auditor

```bash
pip install 'sentinel-kernel[pdf]'
sentinel evidence-pack --output audit.pdf
```

The PDF is self-contained (no external resources), carries the hash
manifest, schema version, sovereignty metadata, and sample trace
records. See a real one: [audit-evidence-pack-sample.pdf](../samples/audit-evidence-pack-sample.pdf).

## Your own organisational gap — answered honestly

- If your readiness score is < 80 %, run `sentinel fix kill-switch` and
  `sentinel fix retention --days 2555`. Two commands, 20 points.
- If after that you're at 80 % and stuck, the remaining 20 % is always
  the same three things: production storage backend choice, signing
  key provenance, and Annex IV authorship. The library cannot close
  these. That is the honest ceiling of a middleware layer.

## Pilot / walkthrough

Public and tracked:
[Open a pilot enquiry on GitHub](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot&template=pilot_enquiry.md)
— for deployment, audit preparation, or BSI pre-engagement help.
No marketing emails. Engagement is scoped individually
([docs/commercial.md](../commercial.md)).
