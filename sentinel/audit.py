"""sentinel.audit — query and independently verify decision records.

This module exposes the *Audit* verb of the canonical
Trace → Attest → Audit → Comply lifecycle. The audit layer exposes
decisions for review: policy compliance checks, counterfactual
inspection, and regulator access. Queries are deterministic and
offline.

Example
-------
.. code-block:: python

    from datetime import datetime, UTC, timedelta
    from sentinel import Sentinel
    from sentinel import audit
    from sentinel.trace import PolicyResult

    sentinel = Sentinel()

    denies = audit.query(
        sentinel,
        policy_result=PolicyResult.DENY,
        since=datetime.now(UTC) - timedelta(days=30),
        limit=100,
    )

    for trace in denies:
        result = audit.verify_trace(sentinel, trace.trace_id)
        assert result.ok

Sovereignty guarantees
----------------------
Fully offline. No network calls. Queries hit only the configured
local storage backend.
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
    """Retrieve decision traces matching the given filters.

    Delegates to the configured storage backend for the base query
    and then applies timestamp filtering in Python. Returned traces
    are ordered most-recent-first.

    :param sentinel: configured :class:`Sentinel` instance.
    :param project: filter by project name; ``None`` = any project.
    :param agent: filter by agent name; ``None`` = any agent.
    :param policy_result: filter by ALLOW / DENY / EXCEPTION_REQUIRED.
    :param since: include only traces with ``started_at >= since``.
    :param until: include only traces with ``started_at < until``.
    :param limit: maximum traces to return after filtering.
    :returns: list of :class:`DecisionTrace`.
    """
    # Fetch a generous page, then filter client-side for timestamp
    # bounds. For deployments with very large stores, prefer
    # narrower ``project`` / ``agent`` filters to reduce pressure on
    # this path.
    page_size = max(limit * 4, 1000)
    raw = sentinel.storage.query(
        project=project,
        agent=agent,
        policy_result=policy_result,
        limit=page_size,
        offset=0,
    )

    def _in_window(trace: DecisionTrace) -> bool:
        started = trace.started_at
        if since is not None and started is not None and started < since:
            return False
        return not (
            until is not None and started is not None and started >= until
        )

    filtered = [t for t in raw if _in_window(t)]

    # Most-recent-first ordering. Traces without started_at fall to
    # the end of the list rather than raising.
    def _sort_key(t: DecisionTrace) -> datetime:
        return t.started_at or datetime.min

    filtered.sort(key=_sort_key, reverse=True)
    return filtered[:limit]


def verify_trace(sentinel: Sentinel, trace_id: str) -> IntegrityResult:
    """Verify the integrity of a single stored trace.

    Returns an :class:`IntegrityResult` describing whether the trace
    exists and whether its stored hashes are consistent with the
    payload.
    """
    return sentinel.verify_integrity(trace_id)


__all__ = [
    "query",
    "verify_trace",
]
