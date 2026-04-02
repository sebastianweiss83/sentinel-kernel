# Sentinel — Claude Instructions

## What this project is

Sentinel is an EU-sovereign AI decision middleware kernel.
It sits in the execution path of any AI agent and turns every decision
into a structured, auditable, sovereign artifact.

The sovereignty is the product. Everything else is implementation detail.

- License: Apache 2.0, permanently
- Governance: Linux Foundation Europe candidate
- Target: BSI reference implementation for EU-sovereign AI decision infrastructure

## Why this exists

Enterprise AI platforms capture decision traces — the exceptions, overrides,
and cross-system context that currently die in chat threads and calls.
The leading platforms are excellent. They are also American, fully subject
to the US CLOUD Act.

For European regulated industries — defence, critical infrastructure,
financial services, healthcare — a US-owned system of record for AI decisions
is not a procurement preference. It is a structural barrier.

EU AI Act Art. 12, 13, 17 mandates audit trails and explainability for
high-risk AI from 2 August 2026. No US provider can deliver this from
their jurisdiction. Sentinel is the answer.

## The three invariants — never break these

1. No US CLOUD Act exposure in the critical path.
2. Air-gapped must always work. If it breaks offline, it is not complete.
3. Apache 2.0, forever. No enterprise edition. No licence key. No relicensing.

## The decision trace

Every trace must contain:
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

## Before adding any dependency

Document in your PR:
1. Who is the parent company?
2. Is it US-incorporated and subject to CLOUD Act?
3. Does it make network calls at runtime?
4. Does it work fully offline?

If 2 and 3 are both yes: do not add to the critical path.

## Code principles

- Explicit over implicit
- Offline-first — no feature is complete until tested without network
- No proprietary formats — traces must be portable
- Storage is pluggable — no backend is mandatory
- Breaking changes to the trace schema require an RFC (/project:rfc)
- Never swallow errors silently

## Deployment contexts

- Air-gapped classified (no network, local storage only)
- On-premise enterprise (EU-sovereign infrastructure)
- Sovereign edge (EU data residency required)

Test against the most constrained context first.
