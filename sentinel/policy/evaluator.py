"""
sentinel.policy.evaluator
~~~~~~~~~~~~~~~~~~~~~~~~~
Policy evaluation interface and implementations.

The NullPolicyEvaluator is the default — it allows everything.
The OPAEvaluator uses Open Policy Agent (OPA) Rego policies.

Future: RegoEvaluator (embedded, no OPA server needed).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from sentinel.core.trace import PolicyEvaluation, PolicyResult

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace


class PolicyEvaluator(ABC):
    """Abstract policy evaluator. Plug in any policy engine."""

    @abstractmethod
    async def evaluate(
        self,
        policy_path: str,
        inputs: dict,
        trace: DecisionTrace,
    ) -> PolicyEvaluation:
        ...


class NullPolicyEvaluator(PolicyEvaluator):
    """
    Default evaluator — allows everything, records that no policy ran.
    Used when no policy_evaluator is provided to Sentinel.
    """

    async def evaluate(
        self,
        policy_path: str,
        inputs: dict,
        trace: DecisionTrace,
    ) -> PolicyEvaluation:
        return PolicyEvaluation(
            policy_id=policy_path,
            policy_version="null",
            result=PolicyResult.NOT_EVALUATED,
            rationale="No policy evaluator configured.",
        )


class LocalRegoEvaluator(PolicyEvaluator):
    """
    Evaluates OPA Rego policies using a local OPA binary.

    Install OPA: https://www.openpolicyagent.org/docs/latest/#running-opa
    Then: pip install sentinel-kernel[opa]

    Usage::

        evaluator = LocalRegoEvaluator(opa_binary="/usr/local/bin/opa")
        sentinel = Sentinel(policy_evaluator=evaluator)
    """

    def __init__(self, opa_binary: str = "opa"):
        self.opa_binary = opa_binary

    async def evaluate(
        self,
        policy_path: str,
        inputs: dict,
        trace: DecisionTrace,
    ) -> PolicyEvaluation:
        import asyncio
        import tempfile

        policy_file = Path(policy_path)
        if not policy_file.exists():
            raise FileNotFoundError(f"Policy not found: {policy_path}")

        input_data = {"input": inputs, "trace_id": trace.trace_id}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(input_data, f)
            input_file = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                self.opa_binary, "eval",
                "--data", str(policy_file),
                "--input", input_file,
                "--format", "json",
                "data.sentinel",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                raise RuntimeError(f"OPA evaluation failed: {stderr.decode()}")

            result_data = json.loads(stdout)
            sentinel_result = result_data.get("result", [{}])[0].get("expressions", [{}])[0].get("value", {})

            allowed = sentinel_result.get("allow", False)
            rule_triggered = sentinel_result.get("deny_reason", None)

            return PolicyEvaluation(
                policy_id=policy_path,
                policy_version=self._get_policy_version(policy_file),
                result=PolicyResult.ALLOW if allowed else PolicyResult.DENY,
                rule_triggered=rule_triggered,
                rationale=json.dumps(sentinel_result),
                evaluator="opa-local",
            )
        finally:
            Path(input_file).unlink(missing_ok=True)

    @staticmethod
    def _get_policy_version(path: Path) -> str:
        """Use file modification time as version if no explicit version comment."""
        import hashlib
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()[:8]


class SimpleRuleEvaluator(PolicyEvaluator):
    """
    Lightweight Python-based policy evaluator.
    No OPA required. Good for getting started.

    Usage::

        def my_policy(inputs: dict) -> tuple[bool, str | None]:
            if inputs.get("discount_pct", 0) > 25:
                return False, "discount_exceeds_cap"
            return True, None

        evaluator = SimpleRuleEvaluator({"policies/discount.py": my_policy})
        sentinel = Sentinel(policy_evaluator=evaluator)
    """

    def __init__(self, rules: dict[str, callable]):
        self.rules = rules

    async def evaluate(
        self,
        policy_path: str,
        inputs: dict,
        trace: DecisionTrace,
    ) -> PolicyEvaluation:
        rule_fn = self.rules.get(policy_path)
        if rule_fn is None:
            raise KeyError(f"No rule registered for policy: {policy_path}")

        allowed, reason = rule_fn(inputs)

        return PolicyEvaluation(
            policy_id=policy_path,
            policy_version="python-callable",
            result=PolicyResult.ALLOW if allowed else PolicyResult.DENY,
            rule_triggered=reason,
            evaluator="sentinel-simple",
        )
