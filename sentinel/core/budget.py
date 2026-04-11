"""Client-side spend tracking with a sovereign audit trail.

Every spend entry is a DecisionTrace — local, tamper-resistant,
auditable without any external service. Your spend data never
leaves your infrastructure. Verifiable offline. Air-gapped safe.

Usage::

    from sentinel.core.budget import BudgetTracker

    budget = BudgetTracker(sentinel=my_sentinel, limit=10.0)

    check = budget.check(estimated_cost=0.25)
    if not check.allowed:
        raise RuntimeError(check.reason)

    budget.record(
        "api:mistral",
        actual_cost=0.23,
        context={"model": "mistral/large-2", "tokens": 1200},
    )
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sentinel.core.trace import (
    DecisionTrace,
    PolicyEvaluation,
    PolicyResult,
)

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


@dataclass
class BudgetCheckResult:
    """Result of :meth:`BudgetTracker.check`.

    ``allowed`` is False if the estimated cost would exceed the remaining
    budget, or if the cost value is invalid (negative, NaN, or inf).
    """

    allowed: bool
    current_spend: float
    limit: float
    remaining: float
    reason: str | None = None


def _is_valid_cost(value: float) -> bool:
    if math.isnan(value) or math.isinf(value):
        return False
    return value >= 0


class BudgetTracker:
    """Track AI spend with a sovereign audit trail.

    Sovereignty guarantees: every spend record is a local
    :class:`DecisionTrace` written to the configured Sentinel storage.
    No external service, no API key, no network calls. Works fully
    air-gapped.
    """

    def __init__(
        self,
        sentinel: Sentinel,
        limit: float,
        currency: str = "USD",
    ) -> None:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        self._sentinel = sentinel
        self._limit = float(limit)
        self._currency = currency
        self._spend: float = 0.0
        self._trace_ids: list[str] = []

    @property
    def limit(self) -> float:
        return self._limit

    @property
    def spend(self) -> float:
        return self._spend

    @property
    def remaining(self) -> float:
        return max(0.0, self._limit - self._spend)

    @property
    def currency(self) -> str:
        return self._currency

    def check(self, estimated_cost: float) -> BudgetCheckResult:
        """Check if ``estimated_cost`` would stay within budget.

        Fails closed on invalid cost values (negative, NaN, inf).
        """
        cost = float(estimated_cost)
        if not _is_valid_cost(cost):
            return BudgetCheckResult(
                allowed=False,
                current_spend=self._spend,
                limit=self._limit,
                remaining=self.remaining,
                reason="invalid_cost",
            )
        if cost > self.remaining:
            return BudgetCheckResult(
                allowed=False,
                current_spend=self._spend,
                limit=self._limit,
                remaining=self.remaining,
                reason="budget_exhausted",
            )
        return BudgetCheckResult(
            allowed=True,
            current_spend=self._spend,
            limit=self._limit,
            remaining=self.remaining,
            reason=None,
        )

    def record(
        self,
        action_type: str,
        actual_cost: float,
        context: dict[str, Any] | None = None,
    ) -> DecisionTrace:
        """Record a spend entry as a sovereign DecisionTrace.

        Raises :class:`ValueError` on invalid cost values.
        """
        cost = float(actual_cost)
        if not _is_valid_cost(cost):
            raise ValueError(f"actual_cost must be a finite non-negative number, got {actual_cost!r}")

        self._spend += cost

        payload: dict[str, Any] = {
            "action_type": action_type,
            "cost": cost,
            "currency": self._currency,
            "cumulative_spend": self._spend,
            "limit": self._limit,
        }
        if context:
            payload["context"] = context

        trace = DecisionTrace(
            project=self._sentinel.project,
            agent=f"budget:{action_type}",
            inputs={"action_type": action_type, "currency": self._currency},
            output=payload,
            data_residency=self._sentinel.data_residency,
            sovereign_scope=self._sentinel.sovereign_scope,
            storage_backend=self._sentinel.storage.backend_name,
            policy_evaluation=PolicyEvaluation(
                policy_id="budget-tracker",
                policy_version="1",
                result=PolicyResult.ALLOW,
                evaluator="sentinel-budget",
            ),
            tags={"kind": "budget", "action_type": action_type},
        )
        trace.complete(output=payload, latency_ms=0)
        self._sentinel.storage.save(trace)
        self._trace_ids.append(trace.trace_id)
        return trace

    def status(self) -> dict[str, Any]:
        return {
            "limit": self._limit,
            "currency": self._currency,
            "spend": self._spend,
            "remaining": self.remaining,
            "trace_count": len(self._trace_ids),
            "trace_ids": list(self._trace_ids),
        }
