# v3.4.0 Evidence Release — Blockers & Open Work

**Status: Phases 1–6 complete. Phases 7–8 pending.**
Last updated: 2026-04-20

---

## Phases delivered (pushed to `main`)

| Phase | Commit   | Notes |
|-------|----------|-------|
| 1. Positioning migration           | `5c6d4a5` | All surfaces moved to "Evidence infrastructure for the regulated AI era" + Trace/Attest/Audit/Comply. CHANGELOG history preserved. |
| 2. CLAUDE.md visual-design rewrite | `2c7499a` | V8 canonical (cream + Inter Tight + deep green + Lucide). Dark operational widgets preserved. |
| 3. API verb modules                | `8de014a` | `from sentinel import trace, attest, audit, comply` works. Long-form names preserved as aliases. |
| 4. Ed25519 default signer          | `1f1528e` | Default Sentinel() signs with Ed25519. `[ed25519]` extra bundled into `[pdf]` + `[dev]`. `sentinel key init` CLI. |
| 5. Hash-chain linkage              | `5bd0797` | `ChainNamespace`, genesis hash, `verify_chain`. `sentinel chain verify` CLI. |
| 6. PAdES PDF signing               | `30b5ce0` | `PAdESSigner`, `sentinel.comply.sign/verify`, `sentinel comply sign/verify` CLI. `[pades]` extra bundled into `[pdf]`. |

**Test suite**: 838 passed, 6 skipped, **100 % line + branch coverage**.

---

## Phase 7 — Unified V8 homepage (NOT started)

### Why it blocks v3.4.0

The release success criteria require:

- [ ] Live homepage at `sebastianweiss83.github.io/sentinel-kernel/` uses V8 design language.
- [ ] Live homepage preserves operational substance (stat pills, enforcement countdown, live dashboard widgets, code examples, compliance articles, industry cards).
- [ ] `docs/preview/platform.html` no longer exists; `/platform.html` redirects to `/`.

Phase 7 is therefore on the critical path for the tag.

### Scope (from masterplan)

1. Rewrite `scripts/generate_preview.py` as modular section functions.
2. Merge V8 design register (cream surfaces, deep green accent, Inter Tight, Lucide icons, scroll-triggered journey reveals) with operational widgets (terminal, dashboard, compliance table, countdown) which remain dark-mode.
3. Top-to-bottom structure: V8 hero → enforcement countdown (preserved) → V8 journey (Trace/Attest/Audit/Comply) → outcomes → architecture → dashboard (preserved) → content blocks → code examples (preserved) → compliance articles (preserved) → industry cards (preserved) → roadmap → CTA → footer.
4. CI-authoritative data injection: test count, version, days-to-enforcement, coverage percentage must flow from `collect_state()` / `data.json`, not hardcoded.
5. Remove `docs/preview/platform.html`; add a redirect.

### Recommended approach

- Read the existing V8 (`docs/preview/platform.html`) end-to-end in one session — it is the canonical source of truth for palette, typography, copy, and journey choreography.
- Keep `scripts/generate_preview.py` as a single file (matches repo convention) but refactor into named `_section_*` functions that return HTML strings (pattern already established in the current generator).
- Lift V8's CSS wholesale into the generator's `<style>` block. Use CSS custom properties for all tokens so the visual-design chapter in CLAUDE.md remains accurate.
- JavaScript: keep the existing `data.json` fetch (stat pills and days-count hydration) and add V8's Intersection Observer for journey reveal.
- Defer: real content updates beyond positioning. Phase 1 already aligned the positioning strings.

### Estimated effort

- ~1 focused working day for a clean rewrite with local preview verification and a sanity pass on incognito Pages deploy after push.
- The four shipped technical features (Ed25519, hash-chain, PAdES, RFC-3161) should be surfaced in the V8 trust-signal row and in the "Today" roadmap column once the rewrite is in place.

---

## Phase 8 — Version bump & release (blocked on Phase 7)

Per masterplan CEO decision #6, v3.4.0 is tagged **only after all four features ship together with tests passing and docs aligned**.

- All four features ✓ implemented and tested.
- Docs aligned for positioning (Phase 1).
- Docs **not yet aligned** for the unified V8 homepage.

### Pre-drafted release artefacts

- `RELEASE_NOTES_v3.4.md` is ready to be written once Phase 7 lands. Draft content lives in the commit messages of `5c6d4a5`, `8de014a`, `1f1528e`, `5bd0797`, `30b5ce0`.
- `CHANGELOG.md` v3.4.0 entry to be inserted at the top once Phase 7 lands — title: "Evidence Release".
- Version bump points: `pyproject.toml` → `3.4.0`; `sentinel/__init__.py` → `__version__ = "3.4.0"`.

### Recommended tag procedure (per CLAUDE.md safe-pattern)

```bash
./scripts/push.sh              # push to main
# wait for CI sync-all to finish
RELEASE_SHA=$(git log --format=%H --grep='release:' -1)
git tag v3.4.0 $RELEASE_SHA
git push origin v3.4.0
```

---

## Non-blocking follow-ups (file-level backlog)

- **RFC-3161 timestamp inside PAdES CMS**: currently the RFC-3161 timestamper produces a separate artefact on the evidence-pack hash-manifest page. Embedding it into the PAdES CMS envelope requires pyhanko's `TimestampRequirements` wiring — deferred to v3.5.
- **AttestationLedger persistence**: Phase 5 ships chain primitives and a file-based verifier, but no persistent attestation store. Storage.get_latest_for_namespace() from the masterplan is stubbed — sufficient for current "generate, sign, archive externally" workflows. A proper ledger can follow in v3.5.
- **Automatic PAdES signing in comply.export()**: today the pipeline produces an unsigned PDF and the caller runs `sentinel comply sign` as a second step. Integrating signing into `render_evidence_pdf()` is a one-line change once the cert lifecycle is field-tested.

These three are documented here (not filed as Issues) to avoid prematurely promising roadmap items.
