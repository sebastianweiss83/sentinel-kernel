"""Trace verb of Trace → Attest → Audit → Comply.

Re-exports the decision-trace data types. The runtime interface is
`@Sentinel().trace` (see sentinel.Sentinel); this module exists so
`from sentinel import trace` works as a namespace alongside the
other verb modules.
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
