# Sentinel v3.5+ Backlog

*Issues deferred from the v3.4.1 patch-release audit. Each entry
has priority, rough scope, and acceptance criteria. Not yet issues
in the tracker.*

Last updated: 2026-04-21 (post-v3.4.1).

---

## v3.5 — Must-land before first production pilot

### P1 — End-to-end composite integration test

**Scope:** one test (~100 lines) that exercises the full
Trace → Attest → Audit → Comply pipeline in a single flow:

1. Instantiate `Sentinel()` with Ed25519 default + FilesystemStorage.
2. Run 50 diverse decisions through `@sentinel.trace` with
   a SimpleRuleEvaluator that produces ALLOW, DENY, and
   EXCEPTION outcomes.
3. Generate a chain-linked attestation per decision namespace.
4. Query the audit log for DENYs; verify integrity on each.
5. Export a PAdES-signed evidence pack.
6. Verify the PAdES signature + chain walk-back to genesis.
7. Run `sentinel audit-gap` and assert the score bumps.

**Why:** individual pieces are 100%-tested; the composed
narrative is not. A champion running "the whole thing" today
relies on README prose, not a green test.

**Budget:** half a day.

### P2 — examples/15_credit_agent.py (sector-matched demo)

**Scope:** runnable example matching the credit-agent shown in
the V8 homepage journey. Uses SimpleRuleEvaluator with realistic
credit thresholds (income, debt-to-income, blacklist), produces
chain-linked attestations, exports a PAdES-signed BaFin-sector
evidence pack. `examples/15_credit_agent.py` + test +
reference-output fixture.

**Why:** champion asking "how would I build the credit-agent you
show on the homepage?" currently has no single doc to follow.

**Budget:** half a day.

### P3 — docs/key-management.md (rotation, revocation, HSM)

**Scope:** operational playbook covering:

- Default key path, permission model, env overrides.
- Rotation primitive (currently missing) — new CLI:
  `sentinel key rotate` that generates a new key, keeps the old
  one as `ed25519.key.1` for verification of old traces, and
  updates the signer.
- Revocation: how to publish a compromise announcement; how to
  mark post-compromise traces as suspect.
- HSM integration contract (`Signer` protocol; YubiHSM / AWS
  KMS / Thales Luna reference shims in the `contrib/` tree).
- Backup + escrow recommendations.

**Why:** first question from every CISO after the demo. Currently
unanswered anywhere in the repo.

**Budget:** one full day for the doc + the `rotate` primitive.

---

## v3.5 — Should-land (nice-to-have)

### P4 — Concurrent chain-append race fix

**Scope:** implement `Storage.get_latest_for_namespace(ns)` with
atomic read-then-append semantics across all three backends
(SQLite, PostgreSQL, Filesystem). Add a new primitive
`sentinel.chain.append(sentinel, namespace, data)` that reads
the latest, computes `previous_hash`, and appends — with row-
level locking on the RDBMS backends and an advisory lockfile on
the filesystem backend.

**Why:** today two concurrent writers in the same agent
namespace will both hash-link to the same `previous_hash` and
produce a fork. Not visible until you scale past one process.

**Budget:** one day. Non-trivial concurrency testing required.

### P5 — Full PAdES-B-LT verification

**Scope:** extend `sentinel/crypto/pades_signer.py::verify_pdf`
beyond structural to cryptographic. Check:

- CMS signature validates against embedded signer certificate.
- Signer certificate chain validates against the OS trust store
  (or a pinned root set passed in by the caller).
- OCSP or CRL status of the signer cert at signing time.
- Embedded RFC-3161 timestamp token validates (already solved in
  v3.4.1 for stand-alone tokens; need to wire the helper in).

**Why:** the `verify_pdf` docstring admits structural-only; a
real PAdES-B-LT verifier (Adobe Reader, Foxit, pyhanko's own
validator) goes further. Closing this gap lets us claim
"independently verifiable to any PAdES-conformant tool."

**Budget:** 1.5 days. pyhanko.sign.validation has most of the
primitives; need to assemble + test.

### P6 — Airgap coverage for v3.4 features

**Scope:** extend `tests/test_airgap.py` with three new tests
under `SENTINEL_AIRGAP=1`:

- `test_airgap_ed25519_key_init_no_network` — first-use key
  creation produces a usable signer offline.
- `test_airgap_chain_verify_no_network` — `verify_chain` walks
  an attestation pack with no socket access.
- `test_airgap_pades_sign_verify_no_network` — comply sign +
  verify round-trip without a TSA reachable.

**Why:** air-gapped is a core Sentinel invariant; the v3.4
features are NOT covered by the existing airgap suite. A hostile
BSI reviewer will ask. Small scope.

**Budget:** half a day.

### P7 — docs/api-stability.md reflects all 23 CLI commands

**Scope:** the STABLE-CLI table in `docs/api-stability.md`
currently lists 12 commands; the package ships 23. Add the
missing rows (`attestation`, `keygen`, `comply`, `chain`, `key`,
`audit`, `ci-check`, `quickstart`, `status`, `audit-gap`, `fix`,
`evidence-pack`). Mark `evidence-pack` as DEPRECATED from v3.4.1.

**Why:** the stability contract should match reality. Enterprise
buyers read api-stability.md before approving.

**Budget:** 30 minutes.

---

## Ideas / not scoped

- **Model-routing sub-capability under Sentinel Federation**
  (issue #24). Scoped to v4.x per CLAUDE.md roadmap.
- **EU-sovereign build pipeline** (issue #21). Phase 4 work.
- **LF Europe formal application** (issue #19). Separate governance
  track.
- **BSI IT-Grundschutz formal assessment** (issue #20). Separate
  certification track, runs alongside v3.x development.
