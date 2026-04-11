# Sentinel — Claude Instructions

<!-- CLAUDE_MD_AUTO_START -->

<!-- This block is rewritten by scripts/update_claude_md.py. Do not edit by hand. -->

## Current state

| | |
|---|---|
| Version | `1.1.0` |
| Tests | 315 passing |
| Coverage | 96% |
| Smoke test | 40/40 ✓ |
| Last updated | 2026-04-11 13:58 UTC |

## Last 5 commits

- `11a7582` chore: gitignore .claude/scheduled_tasks.lock
- `beb5694` feat: manifesto — GDPR, retention, audit integrity, BSI requirements
- `1473521` chore(auto): refresh CLAUDE.md state block [skip ci]
- `290d0c8` fix: mypy type args in cli.py — dict → dict[str, Any]
- `56c05fe` docs: technical co-founder onboarding kit + ADR-001/002/003

## Open issues

- **#2** v0.5: LangFuse integration _(labels: roadmap, integration)_
- **#3** good first issue: add more policy examples _(labels: good first issue)_
- **#5** v1.0: BSI IT-Grundschutz formal assessment _(labels: roadmap, bsi)_
- **#6** v1.0: Linux Foundation Europe application _(labels: roadmap, governance)_
- **#7** RFC-001: SovereigntyManifest feedback wanted _(labels: rfc, discussion)_
- **#8** good first issue: add policy examples for healthcare _(labels: good first issue)_
- **#9** good first issue: VS-NfD deployment guide _(labels: documentation, good first issue)_
- **#11** v1.1: VS-NfD deployment profile (roadmap) _(labels: roadmap)_
- **#12** good first issue: Haystack integration _(labels: good first issue, integration)_
- **#13** good first issue: Rust implementation of SovereigntyManifest (RFC-001) _(labels: good first issue, rfc)_
- **#14** enhance: LangFuse integration — dedicated sovereignty panel _(labels: enhancement)_

<!-- CLAUDE_MD_AUTO_END -->

## What this project is

Sentinel is an EU-sovereign AI decision middleware kernel.
It sits in the execution path of any AI agent and turns every decision
into a structured, auditable, sovereign artifact.

The sovereignty is the product. Everything else is implementation detail.

- License: Apache 2.0, permanently
- Governance: Linux Foundation Europe intended (formal engagement planned with v1.0)
- Target: BSI reference implementation for EU-sovereign AI decision infrastructure

## Why this exists

The leading AI decision platforms are excellent. They are also American,
fully subject to the US CLOUD Act. For European regulated industries —
defence, critical infrastructure, financial services, healthcare — a
US-owned decision record layer is a structural barrier, not a preference.

EU AI Act Art. 12, 13, 17 mandates audit trails for high-risk AI from
2 August 2026. No US provider can deliver this from their jurisdiction.
Sentinel is the open, sovereign answer.

Proprietary platforms are building developer ecosystems with SDKs,
community registries, and framework connectors — all locked to their
ontology and jurisdiction. Sentinel is the alternative: open, portable,
sovereign. The v0.3 LangChain integration meets developers where they are —
automatic trace capture for the most widely-used agent framework.

## The three invariants

1. No US CLOUD Act exposure in the critical path.
2. Air-gapped must always work. If it breaks offline, it is not complete.
3. Apache 2.0, forever. No enterprise edition. No licence key. No relicensing.

## The decision trace — mandatory fields

- Unique trace ID (immutable after creation)
- Timestamp in UTC
- Agent name and version
- Model provider and version
- Policy name, version, result (ALLOW / DENY / EXCEPTION)
- Which rule triggered (if DENY)
- Hashed inputs — never raw PII by default
- Output
- Sovereign scope (EU / LOCAL)
- Data residency assertion

These are the EU AI Act Art. 12/13/17 compliance evidence and the BSI audit trail.

## Before adding any dependency — document in PR

1. Who is the parent company?
2. US-incorporated and subject to CLOUD Act?
3. Makes network calls at runtime?
4. Works fully offline?

If 2 and 3 are both yes: not in the critical path.

## Code principles

- Offline-first — no feature is complete until tested without network
- No proprietary formats — traces must be portable
- Storage is pluggable — no backend is mandatory
- Breaking changes to the trace schema require an RFC (/project:rfc)
- Never swallow errors silently — a missing trace is worse than a crash

## Deployment contexts

- Air-gapped classified (no network, local storage only)
- On-premise enterprise (EU-sovereign infrastructure)
- Sovereign edge (EU data residency required)

Test against the most constrained context first.
