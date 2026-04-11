# SENTINEL — Claude Code Reference

Persistent reference for every Claude Code session working on
`sentinel-kernel`. Read this before touching any code.

---

## What this project is

EU-sovereign AI decision middleware kernel. Python. Apache 2.0
permanently, no enterprise edition, no CLA that enables relicensing.

- **PyPI:** `sentinel-kernel`
- **GitHub:** `sebastianweiss83/sentinel-kernel`
- **Pages preview:** https://sebastianweiss83.github.io/sentinel-kernel/
- **Target governance:** Linux Foundation Europe (formal engagement at v1.0)
- **Target certification:** BSI IT-Grundschutz (Q4 2026 pre-engagement)

Sovereignty is the product. Everything else is implementation detail.

---

## Current state (update on every release)

| | |
|---|---|
| Version | `1.0.1` |
| Tests | **304 passing** |
| Coverage | **97%** |
| Smoke test | 40/40 |
| Python | `>=3.11` |
| License | Apache 2.0 |
| Status | `Development Status :: 5 - Production/Stable` |

---

## The three invariants (never violate)

1. **Local sovereign storage is ALWAYS written before any OTel export.**
   Every `DecisionTrace` lands in the configured `StorageBackend` first.
   OTel is additive observability, never the primary record. If OTel
   fails, the sovereign record still exists.
2. **No US-owned dependency in the critical path.** Runtime, CI/CD,
   and infra are all scanned. Optional extras may be US-owned only if
   the main path still works without them. Enforced by the sovereignty
   scanner and by `test_airgap.py`.
3. **Air-gap must always pass.** Any network call in the core path is
   an `AIRGAP VIOLATION`. `tests/test_airgap.py` blocks `socket.connect`
   at the OS level and runs on every PR. A feature is not complete
   until it passes this gate.

---

## Real API — read this before writing any code example

### Correct imports

```python
from sentinel import Sentinel, DataResidency, PolicyResult
from sentinel import PolicyDeniedError, KillSwitchEngaged
from sentinel.policy.evaluator import (
    NullPolicyEvaluator,
    SimpleRuleEvaluator,
    LocalRegoEvaluator,
)
from sentinel.storage.sqlite import SQLiteStorage
from sentinel.storage.filesystem import FilesystemStorage
from sentinel.storage.postgres import PostgresStorage  # optional extra
```

### Correct constructor

```python
sentinel = Sentinel(
    policy_evaluator=SimpleRuleEvaluator({"p.py": my_rule}),
    storage=SQLiteStorage("./traces.db"),
    project="my-agent",
    sovereign_scope="EU",
    data_residency=DataResidency.LOCAL,   # or the string "local"
)
```

- Keyword is `policy_evaluator=`, **not** `policy=`.
- `data_residency` accepts both the `DataResidency` enum and a string.
- `project` is required for query filtering.

### Decorator

```python
@sentinel.trace(policy="policies/approval.py")
async def approve(request: dict) -> dict:
    ...
```

- `@sentinel.trace` works on sync and async functions.
- Omitting `policy=` runs with `NullPolicyEvaluator` (records
  `NOT_EVALUATED`).
- Raises `PolicyDeniedError` on DENY, `KillSwitchEngaged` on halt.

### Kill switch (EU AI Act Art. 14)

```python
sentinel.engage_kill_switch(reason="Regulatory audit in progress")
# All subsequent @sentinel.trace calls:
#   1. Record a DecisionTrace with policy_result=DENY
#   2. Record a HumanOverride with the reason
#   3. Raise KillSwitchEngaged(reason)

assert sentinel.kill_switch_active is True

sentinel.disengage_kill_switch(reason="Audit complete")
```

Thread-safe. No restart required.

---

## Module map

```
sentinel/core/tracer.py         Sentinel class, @trace, kill switch,
                                PolicyDeniedError, KillSwitchEngaged
sentinel/core/trace.py          DecisionTrace, PolicyEvaluation,
                                HumanOverride, PolicyResult, DataResidency

sentinel/policy/evaluator.py    PolicyEvaluator ABC, NullPolicyEvaluator,
                                SimpleRuleEvaluator, LocalRegoEvaluator

sentinel/storage/base.py        StorageBackend ABC
sentinel/storage/sqlite.py      SQLiteStorage (default)
sentinel/storage/filesystem.py  FilesystemStorage (NDJSON, air-gap ref)
sentinel/storage/postgres.py    PostgresStorage (optional extra, append-only)

sentinel/scanner/runtime.py         RuntimeScanner + 60+ package DB
sentinel/scanner/cicd.py            CICDScanner
sentinel/scanner/infrastructure.py  InfrastructureScanner
sentinel/scanner/knowledge.py       JURISDICTION_DB, CLOUD Act flags

sentinel/manifesto/base.py      SentinelManifesto, requirement classes:
                                EUOnly, OnPremiseOnly, Required,
                                ZeroExposure, Targeting, AcknowledgedGap,
                                ManifestoReport, Gap, MigrationPlan

sentinel/compliance/euaiact.py  EUAIActChecker, ComplianceReport,
                                ArticleStatus (Art. 9/10/11/12/13/14/15/17/72)

sentinel/integrations/langchain.py  SentinelCallbackHandler
sentinel/integrations/otel.py       OTelExporter (local-first)
sentinel/integrations/langfuse.py   LangFuseEnricher (trace-id join)

sentinel/dashboard/html.py      HTMLReport (zero external URLs)
sentinel/dashboard/terminal.py  TerminalDashboard + TerminalReport alias

sentinel/cli.py                 argparse CLI — scan, compliance, report,
                                dashboard, manifesto
```

---

## CLI commands

```
sentinel scan [--runtime|--cicd|--infra|--all] [--json] [--repo PATH]
sentinel compliance check [--html] [--json] [--output FILE]
sentinel report [--output FILE] [--manifesto module:Class] [--repo PATH]
sentinel dashboard [--frames N] [--interval SECONDS]
sentinel manifesto check <file.py:Class | pkg.module:Class> [--json]
```

No subcommand prints help and exits 1.
`compliance` / `manifesto` without their sub-verb also print help and exit 1.

---

## Release process (3 commands forever)

```bash
git commit -am "chore: vX.Y.Z"
git tag vX.Y.Z
git push origin vX.Y.Z
```

GitHub Actions (`.github/workflows/release.yml`) builds and publishes
to PyPI automatically via OIDC trusted publisher — no tokens, no
manual upload.

Full runbook: [`docs/releasing.md`](docs/releasing.md).

---

## Working principles for Claude Code

- **Read actual source before writing any code example.** Never
  invent imports, class names, or constructor kwargs. This file is
  a summary — the source is the truth.
- **`pytest tests/ -q` after every change.** Never proceed on red.
- **Never push to main without `python examples/smoke_test.py`
  returning 40/40.**
- **No named partners / customers / organisations** in any file.
  Industry scenarios must be generic (defence, healthcare, financial
  services, public sector). Only `Sebastian Weiss` may appear as the
  maintainer.
- **Optional dependencies must guard with a helpful `ImportError`**
  at the top of the integration module, pointing at the extras install
  command. Never put optional deps in `sentinel/core/`.
- **Every new file gets a module docstring.** No comments that just
  describe what the code does — only `why` comments that capture
  hidden constraints.
- **Update `CHANGELOG.md` and bump `__version__` in both
  `pyproject.toml` and `sentinel/__init__.py` before tagging.**
- **After every push that changes repo description, topics, or
  homepage:** `gh repo edit` to match.
- **Hooks may rewrite commit messages.** If you see a commit with an
  unexpected message containing your diff, do NOT force-push to
  rewrite history — add a follow-up commit with the correct message.

## Auto-sync contract (non-negotiable)

After **every** push to main, CI runs `scripts/sync_all.py` and
commits any changes. The targets are:

- `CLAUDE.md`              — ground truth for Claude Code sessions
- `README.md`              — badges between `SYNC_ALL_README` markers
- `docs/project-status.md` — full current state (fully auto-generated)
- `docs/preview/`          — GitHub Pages preview content

**Never manually edit these four files.** They will be overwritten
by the next sync run. Curated prose lives outside the marker
blocks; touch that and it will stick.

Workflows:
- `.github/workflows/ci.yml:sync-all` — runs on every push to main
  after tests are green, uses a regenerate-reset-push loop to
  survive races, then uploads the GitHub Pages artifact.
- `.github/workflows/ci.yml:deploy-pages` — runs after `sync-all`
  and publishes the preview.
- `.github/workflows/release.yml:sync-after-release` — runs
  immediately after a PyPI publish so the preview reflects the
  new version within minutes.

Manual sync:
```bash
python scripts/sync_all.py
git add -A && git commit -m "chore: manual sync" && git push origin main
```

The sync is idempotent — running it twice on the same HEAD produces
byte-identical output. Non-determinism must be eliminated at the
source (e.g. pin timestamps to HEAD commit date, not wall clock).

---

## Strategic context

Held outside the repo in the `Sentinel` project in claude.ai. This
file is public and must stay generic.

---

## Roadmap

```
v0.9.0  ✅ 2026-04-11  Complete sovereignty platform
v0.9.1  ✅ 2026-04-11  40-step smoke test + Pages preview + scrub
v1.0.0  ✅ 2026-04-11  Stable — coverage hardened on policy + manifesto
v1.0.1  ✅ 2026-04-11  Coverage hardening + cleanup + release runbook
v1.1    ⏳ 2027-Q1    VS-NfD deployment profile (issue #11)
v2.0    ⏳ 2026-Q4    BSI IT-Grundschutz certification (issue #5)
                      Linux Foundation Europe stewardship (issue #6)
```

---

## Open issues

| # | Title |
|---|---|
| 5 | v1.0: BSI IT-Grundschutz formal assessment |
| 6 | v1.0: Linux Foundation Europe stewardship application |
| 7 | RFC-001: SovereigntyManifest feedback wanted |
| 8 | good first issue: add policy examples for healthcare |
| 9 | good first issue: VS-NfD deployment guide |
| 11 | v1.1: VS-NfD deployment profile (roadmap) |
| 12 | good first issue: Haystack integration |
| 13 | good first issue: Rust implementation of SovereigntyManifest |
| 14 | enhance: LangFuse integration — dedicated sovereignty panel |

Discussion #15: RFC-001 comment thread (14-day period).

---

Last updated: **2026-04-11**, v1.0.1. Update this file on every
release before tagging.
