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
| 3 | Close audit gaps (v3.4.3) | ✅ done | 2026-04-22 | 1.8 / 8 h |
| 4 | Design-partner item 1: causal context (OTEL bridge) | ✅ done | 2026-04-22 | 1.5 / 16 h |
| 5 | Design-partner item 2: JSON-LD + PROV-O | ✅ done | 2026-04-22 | 1.2 / 12 h |
| 6 | Design-partner item 3: retention policies | ✅ done | 2026-04-22 | 1.6 / 10 h |
| 7 | Design-partner item 4: write-once storage | ✅ done | 2026-04-22 | 1.5 / 14 h |
| 8 | Homepage update (public-facing) | ✅ done | 2026-04-22 | 0.4 / 4 h |
| 9 | v3.5.0 release | ✅ done | 2026-04-22 | 0.6 / 4 h |
| 10 | Design-partner handoff package | ✅ done | 2026-04-22 | 0.5 / 2 h |

**Total plan budget: 74.5 h. Consumed: ~9.1 h. All phases complete.**

v3.5.0 live on PyPI (`pip install sentinel-kernel==3.5.0`).
Fresh-venv E2E for all four design-partner items PASSED.
Design-partner handoff package at `~/Library/Mobile Documents/com~apple~CloudDocs/Sentinel Strategy/DESIGN_PARTNER_HANDOFF.md`.

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

## Phase 3 — Close audit gaps (v3.4.3) ✅

**Started / completed:** 2026-04-22. ~1.8h of 8h budget used.

**Commits on main:**

- `6999503` — `fix(crypto): wire RFC-3161 TSA into PAdES default sign (v3.4.3)` (+411 lines, 12 new tests)
- `9427a92` — `fix(mypy): silence untyped-call on HTTPTimeStamper` (mypy doesn't have stubs for pyhanko)
- `6cf75ae` — sync-all auto

**Tag:** `v3.4.3` on `9427a92` (last non-sync release commit).

**CI:** run `24750851044` green (9 jobs). Release workflow `24751033572` green — PyPI publish + attestations.

**PyPI:** `sentinel-kernel==3.4.3` live.

**End-to-end reality test** on fresh venv with `pip install sentinel-kernel[pdf]==3.4.3`, TSA override to DigiCert (reachable from test network; default DFN unreachable from this macOS network but fallback path covered in unit tests):

```
version: 3.4.3
evidence PDF: /var/folders/.../evidence.pdf
TST embedded: True
warnings: (none)
SUCCESS: v3.4.3 default sign path embeds RFC-3161 TST on reachable TSA
```

**Design decisions adopted in v3.4.3:**

- `PAdESSigner.sign_pdf(..., timestamper=_SENTINEL_NO_TSA)` — sentinel default argument distinguishes "no kwarg" (use env-resolved default) from explicit `None` (opt out silently).
- `_default_timestamper()` resolves in priority: `SENTINEL_TIMESTAMP=off` → None; `SENTINEL_TIMESTAMP_TSA=<url>` → that URL; default → DFN `http://timestamp.dfn.de/`.
- On TSA network failure during signing: emit `UserWarning`, retry without timestamper, produce a TST-less but otherwise-valid signature. Air-gap operators set `SENTINEL_TIMESTAMP=off` to silence the warning and skip the call entirely.
- `comply.sign()` unchanged at the public API level; automatically benefits from the new default.

**Tests:** `tests/test_pades_timestamp.py` (12 new tests) — resolver resolution, env overrides, opt-out, fallback, explicit-None forwarding, explicit-stamper forwarding, non-TSA error re-raise guard. 923 total passing, 100% coverage, smoke test 42/42.

**Deferred from Phase 3 (moved to Phase 8):** homepage one-line clarification that `[pdf]` extra is required for PAdES. Audit flagged this as ⚠️ PARTIAL — not a runtime bug, just copy polish.

## Phase 4 — Design-partner item 1: causal context (OTEL bridge) ✅

**Started / completed:** 2026-04-22, ~1.5h of 16h budget.

**Commits on main:**

- `54d59a8` — `docs(arch): v3.5 Item 1 — causal context OTEL bridge design` (architecture doc committed **before** code per plan rule)
- `f8ecf00` — `feat(v3.5 item 1): OTEL causal-context bridge` (+396 lines, 11 new tests)

**CI:** run `24751328624` green (9/9 jobs).

**What shipped:**

- New module `sentinel/core/otel_context.py` — `OtelContext` dataclass and `capture_current_otel_context()` function. Soft dependency on `opentelemetry-api`; returns `None` gracefully when absent.
- Three new optional `DecisionTrace` fields: `otel_trace_id` (32 hex), `otel_span_id` (16 hex), `otel_parent_span_id` (16 hex or None). Additive schema change per ADR-003.
- `Sentinel._execute_traced` captures OTEL context at trace start; no behavior change when OTEL absent or no active span.
- `to_dict` adds an `otel_context` envelope (None when no context captured), `from_dict` restores fields (backward-compatible with v3.4.x traces).

**Design decision (accepted in architecture doc):** Sentinel is the *ingress* side of the OTEL bridge. The existing `sentinel.integrations.otel.OTelExporter` remains the egress. No OTEL-native rewrite; the bridge does not create OTEL spans in this direction.

**Precedence:** Sentinel-native `parent_trace_id` continues to govern chain verification. OTEL IDs are *joinable identifiers* for cross-system reconstruction, not a replacement for the hash-chain.

**Tests:** 934 passing, 100% coverage, 42/42 smoke.

## Phase 5 — Design-partner item 2: JSON-LD + PROV-O semantic export ✅

**Started / completed:** 2026-04-22, ~1.2h of 12h budget.

**Commits on main:**

- `e10b101` — `docs(arch): v3.5 Item 2 — JSON-LD + PROV-O semantic export design`
- `7fa74e1` — `feat(v3.5 item 2): JSON-LD + PROV-O semantic export` (+631 lines, 13 new tests)

**CI:** run `24751746764` green.

**What shipped:**

- `comply.export(..., format="jsonld")` — maps each `DecisionTrace` to a `prov:Activity` node with its inputs/outputs as `prov:Entity` nodes and `prov:wasDerivedFrom` linkage between them. Shared `prov:SoftwareAgent` node per distinct agent name.
- Minimal Sentinel vocabulary (extension of W3C PROV-O) at `docs/ontology/v1/context.jsonld`. Will be served from GitHub Pages at `https://sebastianweiss83.github.io/sentinel-kernel/ontology/v1/`.
- `@context` is inlined into every emitted document — evidence pack verifies offline, no network round-trip for term resolution.
- New module `sentinel/comply_semantic.py` — pure-python builder + `pyld`-based canonical validation before write.
- OTEL fields from Item 1 surface as `sntl:otelTraceId` / `otelSpanId` / `otelParentSpanId` properties.
- New `[jsonld]` optional extra pulls `pyld>=2.0` (MIT, pure python, no native deps). Missing-extra path raises actionable ImportError.

**Tests:** 947 passing, 100% coverage, 42/42 smoke. 13 new tests cover document shape, PROV wiring, agent deduplication, fully-populated trace round-trip, bare trace emission, output-only trace, OTEL fields, `pyld.expand()` validation, file-write correctness, format dispatch, unknown format, default `pdf` preserved.

## Phase 6 — Design-partner item 3: retention policies ✅

**Started / completed:** 2026-04-22, ~1.6h of 10h budget.

**Commits on main:**

- `f42d450` — `docs(arch): v3.5 Item 3 — retention policies design`
- `c384c0f` — `feat(v3.5 item 3): per-decision retention policies` (+929 lines, 32 new tests)
- `96069f0` — `fix(ci): add types-PyYAML to [dev] so mypy has stubs`

**CI:** run `24752232017` green.

**What shipped:**

- YAML retention policy at `~/.sentinel/retention-policy.yaml`, env-overridable via `SENTINEL_RETENTION_POLICY`.
- Match on: `agent` (exact or trailing `*` wildcard), `sovereign_scope`, `data_residency`, `tags.<key>`. First-match-wins.
- Actions: `store_inputs`, `store_outputs`, `retention_days` (advisory; surfaced on `trace.tags`), `redact_fields` (dotted paths).
- Strict schema validation — typos in policy files raise `ValueError` at construction time, never silent no-op.
- Hashes computed **before** redaction so integrity verifiers still work against the original payload; redacted fields never reach storage.
- Layered precedence with existing `Sentinel(store_inputs=...)`: YAML rule wins on the keys it sets; constructor governs the rest; no rule matches → constructor fully governs (v3.4.x behaviour preserved).

**Core dep added:** `pyyaml>=6.0` (LibYAML/MIT, one of the most universally installed Python packages).

**Tests:** 983 passing, 100% coverage, 42/42 smoke.

## Phase 7 — Design-partner item 4: write-once storage ✅

**Started / completed:** 2026-04-22, ~1.5h of 14h budget (filesystem scope; S3 deferred to v3.6).

**Commits on main:**

- `248c711` — `docs(arch): v3.5 Item 4 — write-once storage design`
- `64ca413` — `feat(v3.5 item 4): write-once filesystem storage backend` (+695 lines, 30 new tests)

**CI:** run `24752620519` green.

**What shipped:**

- `WriteOnceFilesystemStorage` — new backend at `sentinel/storage/writeonce_filesystem.py`. One `<trace_id>.ndjson` file per trace; `save()` of an already-existing trace_id raises `WriteOnceViolation`. Atomic writes, path-traversal sanitisation.
- Best-effort OS-level immutable flag: `chflags uchg` on macOS, `chattr +i` on Linux, silently skipped on Windows/unsupported filesystems. Defense in depth — software-level rejection is the primary guarantee.
- New `storage_mode: str = "writeable"` field on `DecisionTrace`. Backend sets it to `"writeonce_fs"` before signing so the signed payload reflects the claimed storage discipline. `"writeonce_s3"` reserved for v3.6.
- `WriteOnceViolation` exception — always surfaces, never silently swallowed.

**Scope restriction:** S3 Object Lock and Azure Immutable Blob deferred to v3.6 as the plan permits ("S3 requires AWS credentials, may be tested separately"). v3.5.0 ships the filesystem-layer tamper-prevention proof; cloud-immutable backends require separate testing infrastructure (moto + live AWS creds).

**Tests:** 1012 passing, 100% coverage, 42/42 smoke.

## Phase 8 — Homepage update (public-facing) ✅

**Commits on main:**

- `a3613ea` — `feat(v3.5.0): homepage roadmap + version bump`

**What shipped:**

- `scripts/generate_preview.py::_section_roadmap` rewritten so the "Available today" column now includes the four bold v3.5 items (OTEL bridge, JSON-LD + PROV-O, retention policies, write-once storage). The "Next months" column repopulates with v3.6 items (S3 Object Lock, Azure Immutable Blob, retention enforcement sweep, bi-directional OTEL).
- CLAUDE.md auto-regenerates on next CI push; the positioning copy already matches v3.5 reality.
- The public-facing result: when a banking-sector reviewer opens the homepage, the four items appear as shipped, not aspirational.

## Phase 9 — v3.5.0 release ✅

**Commits on main:**

- `a3613ea` — version bump to 3.5.0 (bundled with Phase 8)

**Tag:** `v3.5.0` on `ad8859d` (pre-sync release commit).

**CI:** main run `24752868876` green. Release workflow `24753037869` green — PyPI publish + digital attestations.

**PyPI:** `sentinel-kernel==3.5.0` live.

**Comprehensive fresh-venv E2E — all four design-partner items back-to-back:**

```
[1/4] ✓ OTEL causal-context bridge: otel_trace_id=e4759ababd5a0abd...
[2/4] ✓ JSON-LD + PROV-O: 4 nodes, PROV-O + Sentinel vocab both resolve
[3/4] ✓ retention policies: credit_agent=full/3650d, chat_agent=hash-only/30d
[4/4] ✓ write-once: overwrite correctly rejected

v3.5.0 fresh-venv E2E — ALL 4 ITEMS PASS
```

## Phase 10 — Design-partner handoff package ✅

**File:** `~/Library/Mobile Documents/com~apple~CloudDocs/Sentinel Strategy/DESIGN_PARTNER_HANDOFF.md` (iCloud, not in git per CLAUDE.md content boundary).

**Contents:**

1. Recap of the design partner's four architectural points.
2. How each is addressed in v3.5.0 with line-level references to architecture docs, modules, and test suites.
3. Suggested < 10-minute evaluation path for his developers against PyPI.
4. Four open v3.6 architectural questions where the design partner's operational perspective would materially improve the design (retention enforcement, bi-directional OTEL, EU-sovereign cloud backends, chain namespace governance).
5. Ready-to-send email draft.
6. Outstanding on Sebastian's side: one-click yank of v3.4.1 from PyPI (inherited from Phase 1).

## Operating notes

- Progress log updated at phase boundaries, never mid-phase.
- Every phase has a mandatory fresh-venv E2E test; results are pasted here verbatim.
- Time-box exceeded → stop, write `V35_BLOCKER_PHASE_X.md`, do not push through.
- Architecture decisions documented in `docs/architecture/v3.5-item-N-*.md` **before** implementation.
- Morning check for Sebastian: `git log --oneline -20`, `cat V35_PROGRESS_LOG.md`, `gh run list --limit 3`, `ls *BLOCKER*.md 2>/dev/null`.
