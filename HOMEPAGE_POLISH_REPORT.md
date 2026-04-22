# Homepage Content Polish v2 — Report

**Branch:** merged to `main` via `0019e0e`
**Status:** ✅ Live on GitHub Pages
**URL:** https://sebastianweiss83.github.io/sentinel-kernel/
**CI run:** [24779446513](https://github.com/sebastianweiss83/sentinel-kernel/actions/runs/24779446513) — all 9 jobs green
**Tests:** 923 passing, 100% coverage, 42/42 smoke
**Time spent:** ~30 min of the 3 h budget

## Source of change

Every content edit landed in a single file — `scripts/generate_preview.py`. GitHub Pages serves `docs/preview/index.html`, which that script regenerates. CHANGELOG.md, README.md, and all code are untouched, per the spec's "website is marketing, not engineering diary" separation.

## Per-change summary

### Change 1 — Hero ✅

- **Eyebrow** now: `Sentinel · v3.4.3 · Trace-to-Trust kernel for regulated AI` (was `The Sentinel Platform · v3.4.3`).
- **H1** now: `The evidence infrastructure` / `for regulated AI.` (was `Evidence infrastructure for the regulated AI era`). Kept the `<br>` between "infrastructure" and "for" to preserve the desktop two-line hero cadence.
- **Subtitle** now the full new paragraph: *"Sentinel is the Trace-to-Trust kernel that turns EU AI Act compliance from a blocker into a baseline. Every agent decision is traced, attested, and sealed at runtime — so your teams stop fighting audits and keep shipping."*
- **Added a "Key benefits" block** with three bullets, bold-lead format:
  1. **Pre-execution, not post-mortem.** …
  2. **Cryptographically bound, legally durable.** …
  3. **One baseline for every stakeholder.** …
- **Trust row** (Apache 2.0, 923 tests passing, 100% branch coverage, Ed25519 attestations, RFC-3161 timestamping, Air-gapped deployable, BSI IT-Grundschutz preparation) **kept unchanged**.
- **CSS** added: `.hero-benefits`, `.hero-benefits-label`, `.hero-benefits ul/li` with accent-green bullet dot and a mobile breakpoint tuning. Same fade-in animation as the rest of the hero at a 0.45 s delay slot.

### Change 2 — Countdown ✅

- Removed the period after "2 August 2026" in the headline.
- Appended the new tagline italicised beneath the body: *"Sentinel customers are already shipping production AI through the same governed path they'll run on August 3rd."*
- Right-side counter label changed from "days remaining" → "days until enforcement" to match spec verbiage.
- **Dynamic day math preserved**: `_countdown_days()` computed `102` for today (2026-04-22 → 2026-08-02). No hardcoding. Number will decrement by 1 per day, auto-synced on every push.
- **CSS** added: `.countdown-tagline` (small, italic, muted).

### Change 3 — "What Sentinel is not" → proactive claim ✅

- **Right column eyebrow** changed from "What Sentinel is not" to "Where Sentinel fits in your stack" — reframes the whole card as positioning rather than negation.
- **Claim H3 (new)**: *"Sentinel is the cryptographic evidence layer that observability and governance tools don't produce."*
- **Subsection 1** retitled "Not observability" (was "Not an observability platform."). Body rewritten: *"Langfuse, Datadog, Arize, and LangSmith give you performance, cost, and drift signals. Sentinel gives you legally durable evidence of what each agent decided."*
- **Subsection 2** retitled "Not governance enforcement". Body: *"Microsoft AGT, OPA, Cedar, and Bedrock Guardrails enforce policies at runtime. Sentinel seals the cryptographic proof that those policies were applied."*
- **Closer** retained but simplified — dropped the leading bold phrase so the positive framing carries the whole paragraph.
- **CSS**: introduced `.positioning-claim` for the new H3 claim (26 px, heavier than the subsection heads) and split the old `h3` styles into a new `h4` level for the "Not observability" / "Not governance" subsection heads.

### Change 4 — Industries: 6 cards → 5 concrete sectors ✅

Retired: Insurance card, Healthcare card (per spec — they can return as case studies later).

New card set with use-case-story bodies:

1. **Banking & Financial Services** — BaFin BAIT §6.3 use case, full narrative: *"A German bank runs credit decisioning, fraud scoring, AML, and transaction approval through Sentinel. When BaFin requests evidence on model drift under BAIT §6.3, they deliver signed evidence packs in minutes — not weeks of log reconstruction."* Tags: EU AI Act · DORA · BaFin BAIT · MaRisk.
2. **Defence & Aerospace** — VS-NfD path with supply-chain scrutiny framing. Tags: EU AI Act · BSI IT-Grundschutz · VS-NfD.
3. **Enterprise Software & AI Platform Providers** — enterprise-software embedded-AI framing. Tags: EU AI Act · ISO 42001 · Customer conformity assessments.
4. **Public Sector & KRITIS** — independent verifiability framing. Tags: EU AI Act · NIS2 · E-Government law.
5. **Industrial Manufacturing** — 15+ year retention and plant lifetimes. Tags: EU AI Act · ISO 42001 · IEC 62443.

**Eyebrow** changed from "Built for regulated industries" → "Where procurement is already active" — aligns with body copy. Head ("Where the deadline bites first.") and lede paragraph unchanged.

### Change 5 — "Consequence" ✅

Not modified. On target.

### Change 6 — Roadmap ✅

**Retired copy:** the full v3.5.0 yank explanation ("A first v3.5.0 implementation was yanked from PyPI after fresh-install verification surfaced critical gaps; the items are back in architecture planning…").

**New copy:** *"Four architectural items raised by design partners. All four have committed design docs under docs/architecture/. Each item re-ships to production only after passing our fresh-venv E2E verification harness — discipline over shipping speed."*

Preserves the engineering-discipline signal, removes the engineering-diary language from a marketing surface. CHANGELOG.md keeps the full yank story unchanged (per spec).

### Change 7 — Get Started CTA ✅

- Body now: *"Sentinel is in design partnership with a select group of regulated enterprises building production-grade agentic AI under the EU AI Act. Request a working session with our team, or explore the code on GitHub."*
- Primary button label changed from "Request a conversation" → "Request a working session" (consistent with body copy).
- Three-button layout (primary + GitHub + runtime briefing) preserved.

---

## Sebastian verification checkpoints

Open **https://sebastianweiss83.github.io/sentinel-kernel/** in an incognito browser (hard-refresh if opening in a tab that was already cached). Confirm each of the following. All 10 were confirmed by CLI `grep` on the live deployment immediately after CI completed.

| # | Checkpoint | Expected result |
|---|------------|-----------------|
| 1 | Hero H1 | `The evidence infrastructure for regulated AI.` |
| 2 | Hero eyebrow | `Sentinel · v3.4.3 · Trace-to-Trust kernel for regulated AI` |
| 3 | Hero subtitle | `turns EU AI Act compliance from a blocker into a baseline` |
| 4 | Hero Key benefits | three bullets, each with a bold lead phrase (`Pre-execution...`, `Cryptographically bound...`, `One baseline...`) |
| 5 | Countdown | italic tagline `Sentinel customers are already shipping...` present under the body text |
| 6 | Positioning card | H3 claim `Sentinel is the cryptographic evidence layer that observability and governance tools don't produce.` |
| 7 | Industries | 5 sectors, first one `Banking & Financial Services` |
| 8 | Banking card body | mentions `BAIT §6.3` |
| 9 | Roadmap v3.5 section | does NOT mention "yanked" or "critical gaps" |
| 10 | Get Started body | `design partnership with a select group` |

If any checkpoint fails (stale cache, CDN lag), pull this branch locally and run:
```bash
diff <(curl -s https://sebastianweiss83.github.io/sentinel-kernel/) docs/preview/index.html
```

Empty diff confirms live matches origin/main.

---

## Adjustments vs. the spec (transparency)

Three places I deviated slightly from the spec — each conservative, each optional to revise:

1. **Countdown layout.** The spec formatted the days-counter as inline bold text (`**[NUMBER] days** until enforcement.`). The existing design uses a large 44 px accent-green day counter on the right side of the section. I kept the existing visual treatment (it's load-bearing as the hero-adjacent attention anchor) and added the new tagline underneath the body text instead. Functional meaning is identical; visual hierarchy is preserved. If you'd rather have the text-only inline format, tell me and I'll flatten it.

2. **Positioning right-column eyebrow** changed from the spec-implicit "What Sentinel is not" to `Where Sentinel fits in your stack` — the original eyebrow would have contradicted the new positive H3 claim inside the same card. Reads honestly with the new content. If you want the old label back, 10-second fix.

3. **Industries section eyebrow** changed from "Built for regulated industries" → "Where procurement is already active". Kept the H2 headline (`Where the deadline bites first.`) and lede paragraph verbatim. The new eyebrow ties into the lede ("…where procurement is already active") and reads as a single arc.

---

## What's untouched (per spec)

- Trace/Attest/Audit/Comply journey section
- Control Plane preview
- Evidence Pack PDF preview
- "Your stack already has most of this" knot-resolver
- EU AI Act Coverage Table (Full / Partial / Conditional / Human action)
- Runtime / Independent / Integration / Lifecycle deep-dives
- Code examples (`from sentinel import Sentinel`)
- The name "Sentinel" everywhere (this was a content polish, not a rename)
- `CHANGELOG.md`, `README.md`, all code files

---

## Operational notes

- Feature branch `homepage-content-polish-v2` merged and deleted. Only `main` remains locally.
- `HOMEPAGE_POLISH_PLAN.md` is in `.gitignore` — local working doc only.
- No code was changed. Pytest still at 923 passing, 100% coverage, smoke 42/42.
- `_countdown_days()` was already computing dynamically; no math change needed. The number on the page self-decrements daily via the existing `SENTINEL_REPORT_TIMESTAMP` / `_countdown_days()` path.
