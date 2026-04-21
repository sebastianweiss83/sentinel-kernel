# v3.5 Architecture Release — Progress Log

Single source of truth for Sebastian's morning check. Updated at every phase boundary.

**Master plan:** `~/Library/Mobile Documents/com~apple~CloudDocs/Sentinel Strategy/SENTINEL_v3.5_MASTER_PLAN.md`

**Working branch:** `v3.5-architecture-release`

## Status at a glance

| Phase | Title | Status | Completed | Hours used / budget |
|-------|-------|--------|-----------|---------------------|
| 0 | Pre-flight | ✅ done | 2026-04-22 | 0.1 / 0.5 h |
| 1 | v3.4.2 packaging fix | ✅ done | 2026-04-22 | ~1.1 / 1.5 h |
| 2 | Full audit of current state | ✅ done | 2026-04-22 | 0.9 / 3 h |
| 3 | Close audit gaps (v3.4.3) | 🏗 in progress | — | — / 8 h |
| 4 | Berthold item 1: causal context (OTEL bridge) | ⏸ blocked by Phase 3 | — | — / 16 h |
| 5 | Berthold item 2: JSON-LD + PROV-O | ⏸ blocked by Phase 4 | — | — / 12 h |
| 6 | Berthold item 3: retention policies | ⏸ blocked by Phase 5 | — | — / 10 h |
| 7 | Berthold item 4: write-once storage | ⏸ blocked by Phase 6 | — | — / 14 h |
| 8 | Homepage update (Marc-visible) | ⏸ blocked by Phase 7 | — | — / 4 h |
| 9 | v3.5.0 release | ⏸ blocked by Phase 8 | — | — / 4 h |
| 10 | Berthold handoff package | ⏸ blocked by Phase 9 | — | — / 2 h |

Total plan budget: **74.5 h**. Consumed: **~1.2 h** (Phases 0 + 1).

## Phase 0 — Pre-flight

**Started / completed:** 2026-04-22 00:33 UTC

- `git status` clean, CI green on tip of main (run 24749654413 success for commit `5a628c3`)
- No stale `HOLD_STATE.md`, `IMPLEMENTATION_NOTES_V341.md`, or `BLOCKERS*.md` artifacts
- Branch `v3.5-architecture-release` created from `main` at `5a628c3`
- This progress log initialized

**Exit:** clean working state, ready for multi-phase work.

## Phase 1 — v3.4.2 packaging fix

**Started / completed:** 2026-04-22 00:16 → 00:24 UTC (prior session turn, before Phase 0 formally opened)

**Summary:** v3.4.1 had `cryptography` in the optional `[ed25519]` extra, so on a fresh `pip install sentinel-kernel` the Ed25519 default signer fell through to `None` and traces shipped unsigned — contradicting the "Ed25519 signatures" canonical trust signal. v3.4.2 moves `cryptography>=42.0` into core `dependencies`.

**Commits on main:**

- `a80f990` — `fix(packaging): move cryptography to core deps (v3.4.2)`
- `0d58a04` — `docs: bump performance.md version header to v3.4.2`
- `c95f694` — `docs: add ED25519_DEFAULT_TEST_REPORT.md (v3.4.2 reality-test log)`
- `5a628c3` — `chore(auto): sync all derived content [skip ci]`

**Tag:** `v3.4.2` on commit `0d58a04` (the pre-sync release commit).

**CI:** `gh run 24749479916` — all 9 jobs green (Test 3.11/3.12, Quickstart smoke 42/42, Lint & type, Sovereignty, Air-gapped, Manifesto, Sync-all, Pages).
**Release workflow:** `gh run 24749701949` — PyPI publish + digital attestations, success.
**PyPI:** `sentinel-kernel==3.4.2` available (confirmed via `pip index versions sentinel-kernel`).

**End-to-end reality test** — fresh venv, `pip install sentinel-kernel==3.4.2`:

```
cryptography installed: 46.0.7
SUCCESS: algorithm=Ed25519, sig_preview=Ed25519:WkgoeS7CoC0soJUDGDRepbPfhYiATIQj
key persisted at /Users/sebastianweiss/.sentinel/ed25519.key mode=0o600
```

Full log: `ED25519_DEFAULT_TEST_REPORT.md` at repo root.

**Tests:** 911 pytest passing, 100% coverage, 42/42 smoke steps.

**Outstanding from Phase 1 (single item):** yank v3.4.1 from PyPI.
CLI yank is blocked — the repo uses trusted-publisher OIDC for release, no long-lived API token locally, no `~/.pypirc`. Sebastian to one-click yank at:
https://pypi.org/manage/project/sentinel-kernel/release/3.4.1/ → Options → Yank.
Reason string to paste verbatim:

> v3.4.1 had a packaging bug: the cryptography dependency was in an optional extra instead of core dependencies, causing Ed25519 default signing to silently no-op on fresh installs. Fixed in v3.4.2.

Until yanked, `pip install sentinel-kernel` still resolves to `3.4.2` (newer wins). Yank only affects users who explicitly pinned `==3.4.1`.

**Exit:** E2E SUCCESS on fresh venv, v3.4.2 on PyPI, marketing-code sync gap closed. Yank is a one-click operator task, not a code blocker.

## Phase 2 — Full audit of current state ✅

**Started / completed:** 2026-04-22 (post-explicit-"go-go-go" authorization), ~50 min elapsed under 3h budget.

**Deliverable:** `AUDIT_v3.4.2.md` at repo root (gitignored). Fresh-venv `pip install sentinel-kernel==3.4.2` tested 13 marketing claims.

**Scorecard:** 10 ✅ VERIFIED · 2 ⚠️ PARTIAL · 1 🟥 BROKEN.

**Key finding (🟥 BROKEN):** Homepage says *"Every evidence pack PDF carries a PAdES signature with EU-sovereign RFC-3161 timestamp."* Code reality: `sentinel.crypto.timestamp.RFC3161Timestamper` exists as a class, but is **not called** from `comply.sign()`, `comply.export()`, `generate_attestation()`, or `render_evidence_pdf()`. `grep -rn` across compliance / core / comply / attest returns zero hits. Inspection of a signed PDF via `pyhanko`: `attached_timestamp_data is None`. Same anti-pattern class as v3.4.1 Ed25519 — capability shipped as standalone class, not wired into default lifecycle. This motivates v3.4.3.

**Partial findings:**
- `[pdf]` extra required for PAdES — honest ImportError, arguably by-design. Will add one-line homepage clarification in Phase 3.
- BSI wording already accurate — says "preparation", not "certified". No change.

**Everything else:** Ed25519 default (re-confirmed post-v3.4.2), hash-chain attestations (tamper-detected), SHA-256 hashing, air-gapped (smoke step 22), 8 integrations (correct class names), 4 verb modules, 23 CLI subcommands, kill switch, Apache 2.0, 911 tests / 100% coverage — all verified.

## Phase 3 — Close audit gaps (v3.4.3)

**Status:** 🏗 in progress. Scope: wire `RFC3161Timestamper` into `comply.sign()` so evidence PDFs actually carry a TSA timestamp by default. Homepage clarification on `[pdf]` extra.

## Operating notes

- Progress log updated at phase boundaries, never mid-phase.
- Every phase has a mandatory fresh-venv E2E test; results are pasted here verbatim.
- Time-box exceeded → stop, write `V35_BLOCKER_PHASE_X.md`, do not push through.
- Architecture decisions documented in `docs/architecture/v3.5-item-N-*.md` **before** implementation.
- Morning check for Sebastian: `git log --oneline -20`, `cat V35_PROGRESS_LOG.md`, `gh run list --limit 3`, `ls *BLOCKER*.md 2>/dev/null`.
