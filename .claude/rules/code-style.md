# Code Style

Trace correctness over performance.
Interfaces over implementations.
No silent failures — a missing trace is worse than a crash.
Offline first — no feature is complete until tested without network.

Every public interface states:
- What it does
- What sovereignty guarantees it provides (or does not)
- What happens with no network connection

No secrets in code, traces, or logs. When in doubt: hash it.
Use /project:rfc before any breaking change to the trace schema.
