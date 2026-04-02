# SKILL: Sovereignty Check

## Auto-trigger when
Any new import or dependency / any network call written / any storage write path changed.

## Checks
- Network calls: destination? In critical path? US-owned? Can disable offline?
  If US-owned and in critical path: VIOLATION. Stop.
- Data residency: data_residency set correctly? sovereign_scope accurate?
  Can a regulator independently verify the claim?
- Offline: does this path work with no network?

## Output
SOVEREIGNTY-SKILL: SOVEREIGN | DEGRADED | VIOLATION
[OK] storage is local — sovereign
[WARN] optional integration uses non-sovereign service — marked
[VIOLATION] dependency sends data to US-owned service in critical path

VIOLATION: stop. Redesign before continuing.
