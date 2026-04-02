# Code Style

Trace correctness over performance. A missing trace is worse than a crash.
Interfaces over implementations. Storage, policy eval, trace emission are interfaces.
Offline first. No feature is complete until tested without network.
No silent failures. No secrets in code, traces, or logs.

Every public interface states:
- What it does
- Sovereignty guarantees it provides (or explicitly does not)
- What happens with no network connection

Use /project:rfc before any breaking change to the trace schema.
