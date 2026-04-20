"""sentinel.trace — decision-trace primitives.

This module exposes the *Trace* verb of the canonical
Trace → Attest → Audit → Comply lifecycle. The primary runtime
interface is the :class:`~sentinel.Sentinel` decorator
(``@Sentinel().trace``); this module re-exports the decision-trace
data types for users who prefer the module-level namespace.

Example
-------
.. code-block:: python

    from sentinel import Sentinel
    from sentinel.trace import DecisionTrace, PolicyResult

    sentinel = Sentinel()

    @sentinel.trace
    async def approve(req: dict) -> dict:
        ...

Sovereignty guarantees
----------------------
No network calls. Fully offline. Trace schema is portable NDJSON.
"""

from __future__ import annotations

from sentinel.core.trace import (
    DataResidency,
    DecisionTrace,
    HumanOverride,
    PolicyEvaluation,
    PolicyResult,
)
from sentinel.core.tracer import (
    IntegrityResult,
    KillSwitchEngaged,
    OutputVerificationResult,
    PolicyDeniedError,
    PreflightResult,
    Sentinel,
)

__all__ = [
    "DataResidency",
    "DecisionTrace",
    "HumanOverride",
    "IntegrityResult",
    "KillSwitchEngaged",
    "OutputVerificationResult",
    "PolicyDeniedError",
    "PolicyEvaluation",
    "PolicyResult",
    "PreflightResult",
    "Sentinel",
]
