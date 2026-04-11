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

from sentinel.core.trace import (
    DataResidency,
    DecisionTrace,
    HumanOverride,
    PolicyEvaluation,
    PolicyResult,
)
from sentinel.core.tracer import KillSwitchEngaged, PolicyDeniedError, Sentinel

__version__ = "1.0.1"
__all__ = [
    "Sentinel",
    "PolicyDeniedError",
    "KillSwitchEngaged",
    "DecisionTrace",
    "PolicyEvaluation",
    "PolicyResult",
    "HumanOverride",
    "DataResidency",
]
