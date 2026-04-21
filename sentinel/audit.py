"""Audit verb of Trace → Attest → Audit → Comply.

Query and independently verify stored decision traces. Everything
here is a thin layer over the storage backend plus
`Sentinel.verify_integrity` — the verb module exists so
`from sentinel import audit` works.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sentinel.core.trace import DecisionTrace, PolicyResult

if TYPE_CHECKING:
    from sentinel.core.tracer import IntegrityResult, Sentinel


def query(
    sentinel: Sentinel,
    *,
    project: str | None = None,
    agent: str | None = None,
    policy_result: PolicyResult | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
) -> list[DecisionTrace]:
    """Return traces matching the filters, most-recent first.

    Timestamp windowing is applied in Python after the storage
    query. Backends that paginate large result sets benefit from
    narrower ``project`` / ``agent`` filters.
    """
    page_size = max(limit * 4, 1000)
    raw = sentinel.storage.query(
        project=project,
        agent=agent,
        policy_result=policy_result,
        limit=page_size,
        offset=0,
    )

    def in_window(t: DecisionTrace) -> bool:
        started = t.started_at
        if since is not None and started is not None and started < since:
            return False
        return not (until is not None and started is not None and started >= until)

    filtered = [t for t in raw if in_window(t)]
    filtered.sort(key=lambda t: t.started_at or datetime.min, reverse=True)
    return filtered[:limit]


def verify_trace(sentinel: Sentinel, trace_id: str) -> IntegrityResult:
    """Recompute the stored trace's hashes and report any drift."""
    return sentinel.verify_integrity(trace_id)


__all__ = ["query", "verify_trace"]
