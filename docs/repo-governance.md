# Sentinel-Kernel Repo Governance

**Status:** Active | **Updated:** April 12, 2026 | **Coverage:** 100%

## Purpose

World-class sovereign decision infrastructure for enterprises.

## Decisions

### Onboarding Hierarchy

- **Primary:** `pipx install sentinel-kernel && sentinel demo`
- **Secondary:** Python SDK (`from sentinel import Sentinel`)
- **Advanced:** Docker / OQS / Grafana / Rust
- Hero terminal → `sentinel demo` walkthrough
- CTA copies → `pipx install sentinel-kernel && sentinel demo`
- CLI tab → first/default in "Start in 2 minutes"

### Design Language

- **Palette:** Emerald (`#34d399`), graphite surfaces
- **Typography:** Strong sans, technical
- **Radii:** 4px / 6px discipline
- **Motion:** Opacity only, restrained
- **Tone:** Sovereign infrastructure
- **Anti-patterns:** AI glow, pill overload, decorative terminal

### Source of Truth

| File | Governs |
|---|---|
| `scripts/generate_preview.py` | Preview / landing page |
| `CLAUDE.md` | Positioning / design / push rules |
| `README.md` | Doc index / badges / quick start |
| `docs/bsi-profile.md` | BSI timeline |

### Coverage Enforcement

- `--cov-fail-under=100 --cov-branch` on full test suite in CI
- CI fails automatically if coverage regresses
- `# pragma: no cover` only for env-dependent import guards
- Focused CI runs use `--no-cov` to avoid false failures

### Multilingual

- English dominant (technical)
- German proper nouns preserved (BSI IT-Grundschutz)

### Workflows

- Human commit → CI → sync_all bot `[skip ci]`
- Tag → Release (PyPI)

## Change Control

**Review before changing:**
- CLI-first hierarchy
- Hero terminal
- Compliance links
- Design tokens
- CLAUDE.md

**Freely changeable:**
- Feature cards
- SDK examples
- Integrations

## Operating Principle

Shortest path to undeniable proof.

## Next Update

Post BWI / Quantum Systems feedback.
