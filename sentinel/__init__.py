"""
Sentinel — evidence infrastructure for the regulated AI era.

The canonical lifecycle is Trace → Attest → Audit → Comply:

- :mod:`sentinel.trace` captures the decision (``@Sentinel().trace``)
- :mod:`sentinel.attest` cryptographically signs the record
- :mod:`sentinel.audit` queries and independently verifies records
- :mod:`sentinel.comply` exports the auditor-grade evidence pack

Example
-------
.. code-block:: python

    from sentinel import Sentinel
    from sentinel.storage import SQLiteStorage

    sentinel = Sentinel(storage=SQLiteStorage("./decisions.db"), project="my-agent")

    @sentinel.trace
    async def my_agent_decision(input: str) -> dict:
        ...

Apache 2.0 License. See LICENSE.
"""

__version__ = "3.3.1"

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

# Canonical v3.4 verb-named modules. Each is a first-class surface of
# the Trace → Attest → Audit → Comply lifecycle.
from sentinel import attest, audit, comply, trace

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
    # v3.4 canonical verb modules
    "trace",
    "attest",
    "audit",
    "comply",
]
