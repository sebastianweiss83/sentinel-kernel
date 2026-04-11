# Sentinel — Claude Instructions

<!-- CLAUDE_MD_AUTO_START -->

<!-- This block is rewritten by scripts/update_claude_md.py. Do not edit by hand. -->

## Current state

| | |
|---|---|
| Version | `2.0.0` |
| Tests | 504 passing |
| Coverage | 100% |
| Smoke test | 40/40 ✓ |
| Last updated | 2026-04-11 16:44 UTC |

## Last 5 commits

- `5bf2bfb` test: infrastructure yaml-exclusion branch (CI 99%→100%)
- `568c702` fix: sync_all idempotency across environments
- `79bbd40` feat: complete auto-sync — all derived content updates on every push
- `ddaa04b` chore: sync CLAUDE.md to v2.0.0 [skip ci]
- `8d0e5b1` feat: v2.0.0 — production stable, BSI assessment ready

## Open issues

- **#3** good first issue: add more policy examples _(labels: good first issue)_
- **#5** v1.0: BSI IT-Grundschutz formal assessment _(labels: roadmap, bsi)_
- **#6** v1.0: Linux Foundation Europe application _(labels: roadmap, governance)_
- **#7** RFC-001: SovereigntyManifest feedback wanted _(labels: rfc, discussion)_
- **#8** good first issue: add policy examples for healthcare _(labels: good first issue)_
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

## Auto-sync contract (non-negotiable)

After **every** push to main, CI runs `scripts/sync_all.py` and
commits any changes. The targets are:

- `CLAUDE.md`              — ground truth for Claude Code sessions
- `README.md`              — badges between `SYNC_ALL_README` markers
- `docs/project-status.md` — full current state (fully auto-generated)
- `docs/preview/`          — GitHub Pages preview content

**Never manually edit these files.** They will be overwritten by the
next sync run. Markers (`SYNC_ALL_*_START/END` or the existing
`CLAUDE_MD_AUTO_*`) delimit the safe regions.

To trigger a manual sync:

```bash
python scripts/sync_all.py
git add -A && git commit -m "chore: manual sync" && git push
```

The sync is idempotent — running it twice on the same HEAD produces
byte-identical output. CI enforces this via a regenerate-reset-push
loop in `.github/workflows/ci.yml:sync-all`.

## Deployment contexts

- Air-gapped classified (no network, local storage only)
- On-premise enterprise (EU-sovereign infrastructure)
- Sovereign edge (EU data residency required)

Test against the most constrained context first.
