# SKILL: Sovereignty Check

## Auto-trigger when
New import or dependency / network call written / storage write path changed.

## Checks
- Network calls: destination? In critical path? US-owned? Can disable offline?
  If US-owned and in critical path: VIOLATION.
- Data residency: data_residency correct? sovereign_scope accurate?
  Can a regulator independently verify?
- Offline: works with no network?

## Output
SOVEREIGNTY-SKILL: SOVEREIGN | DEGRADED | VIOLATION
[OK] storage is local — sovereign
[WARN] optional integration uses non-sovereign service — marked
[VIOLATION] dependency sends data to US-owned service in critical path
