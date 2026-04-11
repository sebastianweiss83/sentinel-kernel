"""
Sentinel — EU-sovereign AI decision middleware.

    from sentinel import Sentinel
    from sentinel.storage import SQLiteStorage

    sentinel = Sentinel(storage=SQLiteStorage("./decisions.db"), project="my-agent")

    @sentinel.trace
    async def my_agent_decision(input: str) -> dict:
        ...

Apache 2.0 License. See LICENSE.
"""

from sentinel.core.attestation import (
    AttestationResult,
    generate_attestation,
    verify_attestation,
)
from sentinel.core.budget import BudgetCheckResult, BudgetTracker
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

__version__ = "2.1.0"
__all__ = [
    "Sentinel",
    "PolicyDeniedError",
    "KillSwitchEngaged",
    "DecisionTrace",
    "PolicyEvaluation",
    "PolicyResult",
    "HumanOverride",
    "DataResidency",
    "IntegrityResult",
    "PreflightResult",
    "OutputVerificationResult",
    "BudgetTracker",
    "BudgetCheckResult",
    "generate_attestation",
    "verify_attestation",
    "AttestationResult",
]
