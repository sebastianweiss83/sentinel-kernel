# /project:security-audit

Security audit for classified deployment readiness.
Think like an attacker targeting an air-gapped environment.
Usage: /project:security-audit [file or "all"]

## Trace integrity
- Can a trace be modified after writing?
- Is the audit trail append-only?
- Hash or signature on stored traces?

## Policy injection
- Can untrusted input influence which policy is loaded?
- Can policy evaluation be bypassed?
- Is the policy path sanitised?

## Secret handling
- Secrets in logs, traces, or errors?
- Sensitive values flowing into traces unredacted?

## Supply chain
- All dependencies pinned? Fetched over encrypted transport?
- Any US-owned dependency in the critical path?

## Air-gapped readiness
- Unexpected outbound network calls?
- DNS lookups that could leak information?
- System works fully isolated?

## Output: Severity + Location + Attack scenario + Fix + Classified blocker YES/NO
