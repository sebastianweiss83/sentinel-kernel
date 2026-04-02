# /project:protocol-review

Review a decision trace or trace-emitting code for EU AI Act compliance and BSI readiness.

## Trace completeness — EU AI Act Art. 12 + 17
- [ ] Unique trace ID, immutable after creation
- [ ] Timestamp in UTC
- [ ] Agent name and version
- [ ] Model provider and version
- [ ] Policy name, version, result (ALLOW / DENY / EXCEPTION)
- [ ] Which rule triggered (if DENY)
- [ ] Inputs hashed — no raw PII unless explicitly opted in
- [ ] Output recorded
- [ ] Sovereign scope: EU or LOCAL
- [ ] Data residency asserted

## Sovereignty
- [ ] No US-controlled component in the critical path
- [ ] Works with zero network connectivity
- [ ] Data residency assertion independently verifiable

## Policy evaluation
- [ ] In-process — no remote call
- [ ] Deterministic
- [ ] DENY records which rule triggered
- [ ] Human override creates a second trace entry linked to the original

## Trace integrity
- [ ] Cannot be modified after writing
- [ ] Storage is append-only
- [ ] Correction is a new entry — never an edit

## Output: PASS / FAIL / NEEDS REVIEW + issues with location + suggested fix
