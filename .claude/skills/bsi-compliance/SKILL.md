# SKILL: BSI Compliance Check

## Auto-trigger when
Any new dependency added / encryption or secret handling touched /
offline path changed / mandatory trace field modified.

## Checks
- Secrets: no hardcoded credentials, no sensitive values in traces or logs
- EU AI Act fields: all mandatory fields present? Any removed without RFC? → BLOCK
- Air-gapped: works with no network? New mandatory outbound call? → BLOCK
- Dependencies: US-owned? Makes network calls? → Flag both

## Output
BSI-SKILL: PASS | WARN | BLOCK
[WARN] new dependency — check ownership and network behaviour
[BLOCK] mandatory trace field removed without RFC
[BLOCK] mandatory network call added — breaks air-gapped deployment

BLOCK means stop. Fix before continuing.
