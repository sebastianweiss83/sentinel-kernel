"""
sentinel.core.tracer
~~~~~~~~~~~~~~~~~~~~
The Sentinel class is the primary entry point.
Wrap any function with @sentinel.trace and it becomes sovereign.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from sentinel.core.trace import (
    DataResidency,
    DecisionTrace,
    HumanOverride,
    PolicyEvaluation,
    PolicyResult,
)
from sentinel.policy.evaluator import NullPolicyEvaluator, PolicyEvaluator
from sentinel.storage.base import StorageBackend
from sentinel.storage.sqlite import SQLiteStorage


class Sentinel:
    """
    The Sentinel kernel.

    Usage::

        sentinel = Sentinel(
            storage=SQLiteStorage("./decisions.db"),
            project="my-agent",
            data_residency=DataResidency.EU_DE,
        )

        @sentinel.trace
        async def my_agent_decision(input: str) -> dict:
            ...

        # Or with a policy:
        @sentinel.trace(policy="policies/approval.rego")
        async def approve_discount(deal, request):
            ...
    """

    def __init__(
        self,
        storage: StorageBackend | str | None = None,
        project: str = "default",
        data_residency: DataResidency = DataResidency.LOCAL,
        sovereign_scope: str = "local",
        policy_evaluator: PolicyEvaluator | None = None,
        store_inputs: bool = True,
        store_outputs: bool = True,
        signer: Any | None = None,
    ):
        # Storage
        self.storage: StorageBackend
        if storage is None:
            self.storage = SQLiteStorage("./sentinel-traces.db")
        elif isinstance(storage, str):
            self.storage = SQLiteStorage(storage)
        else:
            self.storage = storage

        self.project = project
        self.data_residency = data_residency
        self.sovereign_scope = sovereign_scope
        self.policy_evaluator = policy_evaluator or NullPolicyEvaluator()
        self.store_inputs = store_inputs
        self.store_outputs = store_outputs
        self._signer = signer

        # Kill switch state (EU AI Act Art. 14 — human oversight halt)
        self._kill_switch_lock = threading.Lock()
        self._kill_switch_active = False
        self._kill_switch_reason: str | None = None

        self.storage.initialise()

    @property
    def kill_switch_active(self) -> bool:
        """True if the kill switch has been engaged."""
        with self._kill_switch_lock:
            return self._kill_switch_active

    def engage_kill_switch(self, reason: str) -> None:
        """
        Engage the runtime kill switch (EU AI Act Art. 14 halt mechanism).

        Every subsequent @sentinel.trace call will be blocked without
        executing the wrapped function. Each blocked call produces a
        DENY trace with a HumanOverride entry naming the reason.

        Takes effect immediately, no restart required.
        """
        with self._kill_switch_lock:
            self._kill_switch_active = True
            self._kill_switch_reason = reason

    def disengage_kill_switch(self, reason: str) -> None:
        """
        Disengage the runtime kill switch. Normal execution resumes.

        The reason is required for auditability — why was the halt lifted?
        """
        with self._kill_switch_lock:
            self._kill_switch_active = False
            self._kill_switch_reason = None
        _ = reason  # reserved for future audit logging

    def trace(
        self,
        func: Callable[..., Any] | None = None,
        *,
        policy: str | None = None,
        agent_name: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> Callable[..., Any]:
        """
        Decorator that wraps an agent function with sovereign trace capture.

        Can be used with or without arguments::

            @sentinel.trace
            async def my_agent(): ...

            @sentinel.trace(policy="policies/default.rego", tags={"env": "prod"})
            async def my_agent(): ...
        """
        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            name = agent_name or f.__qualname__

            @functools.wraps(f)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await self._execute_traced(
                    f, args, kwargs, name, policy, tags or {}
                )

            @functools.wraps(f)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return asyncio.run(
                    self._execute_traced(f, args, kwargs, name, policy, tags or {})
                )

            if inspect.iscoroutinefunction(f):
                return async_wrapper
            return sync_wrapper

        # Called as @sentinel.trace (no args)
        if func is not None:
            return decorator(func)

        # Called as @sentinel.trace(...) (with args)
        return decorator

    async def _execute_traced(
        self,
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        agent_name: str,
        policy: str | None,
        tags: dict[str, str],
    ) -> Any:
        """Execute a function and capture the full decision trace."""
        # Build inputs dict — preserve kwargs, represent positional args
        inputs = {**kwargs}
        if args:
            inputs["_args"] = [repr(a) for a in args]

        trace = DecisionTrace(
            project=self.project,
            agent=agent_name,
            inputs=inputs if self.store_inputs else {},
            data_residency=self.data_residency,
            sovereign_scope=self.sovereign_scope,
            storage_backend=self.storage.backend_name,
            tags=tags,
        )

        # Kill switch check — happens BEFORE policy eval and BEFORE execution
        with self._kill_switch_lock:
            ks_active = self._kill_switch_active
            ks_reason = self._kill_switch_reason or "kill switch engaged"

        if ks_active:
            trace.policy_evaluation = PolicyEvaluation(
                policy_id="kill-switch",
                policy_version="runtime",
                result=PolicyResult.DENY,
                rule_triggered="kill_switch_engaged",
                rationale=ks_reason,
                evaluator="sentinel-kill-switch",
            )
            trace.human_override = HumanOverride(
                approver_id="kill-switch",
                approver_role="system-halt",
                justification=ks_reason,
            )
            trace.tags["kill_switch"] = "engaged"
            trace.complete(output={}, latency_ms=0)
            self.storage.save(trace)
            raise KillSwitchEngaged(
                f"Sentinel kill switch engaged: {ks_reason}. "
                f"Trace ID: {trace.trace_id}"
            )

        # Policy evaluation — happens BEFORE execution
        if policy:
            policy_eval = await self.policy_evaluator.evaluate(
                policy_path=policy,
                inputs=inputs,
                trace=trace,
            )
            trace.policy_evaluation = policy_eval

            if policy_eval.result == PolicyResult.DENY:
                # Persist the denial trace before raising
                self.storage.save(trace)
                raise PolicyDeniedError(
                    f"Policy '{policy}' denied the action. "
                    f"Rule: {policy_eval.rule_triggered}. "
                    f"Trace ID: {trace.trace_id}"
                )

        # Execute the actual agent function
        start = time.monotonic()
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
        except Exception as exc:
            trace.tags["error"] = type(exc).__name__
            trace.tags["error_message"] = str(exc)[:500]
            elapsed = int((time.monotonic() - start) * 1000)
            trace.complete(output={}, latency_ms=elapsed)
            self._sign_trace(trace)
            self.storage.save(trace)
            raise

        elapsed = int((time.monotonic() - start) * 1000)

        output = result if isinstance(result, dict) else {"result": repr(result)}
        trace.complete(
            output=output if self.store_outputs else {},
            latency_ms=elapsed,
        )

        self._sign_trace(trace)
        self.storage.save(trace)
        return result

    def _sign_trace(self, trace: DecisionTrace) -> None:
        """Sign the trace in place, if a signer is configured.

        Failures are non-fatal: a missing signature is recorded as
        ``signature=None`` so storage never blocks on a crypto error.
        """
        if self._signer is None:
            return
        try:
            payload = trace.to_json().encode("utf-8")
            trace.signature = self._signer.sign(payload)
            trace.signature_algorithm = getattr(self._signer, "algorithm", None)
        except Exception as exc:  # pragma: no cover - defensive
            trace.tags["signing_error"] = f"{type(exc).__name__}:{exc}"[:200]

    @asynccontextmanager
    async def span(
        self,
        agent_name: str,
        policy: str | None = None,
        **tags: str,
    ) -> AsyncIterator[DecisionTrace]:
        """
        Context manager for manual trace control.

        Usage::

            async with sentinel.span("complex_workflow") as trace:
                result = await step_one()
                trace.tags["step_one_result"] = str(result)
                final = await step_two(result)
        """
        trace = DecisionTrace(
            project=self.project,
            agent=agent_name,
            data_residency=self.data_residency,
            sovereign_scope=self.sovereign_scope,
            storage_backend=self.storage.backend_name,
            tags=tags,
        )

        try:
            yield trace
        finally:
            if trace.completed_at is None:
                trace.complete(output=trace.output or {}, latency_ms=0)
            self.storage.save(trace)

    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: PolicyResult | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DecisionTrace]:
        """Query stored decision traces."""
        return self.storage.query(
            project=project or self.project,
            agent=agent,
            policy_result=policy_result,
            limit=limit,
            offset=offset,
        )

    def preflight(self, action_type: str) -> PreflightResult:
        """Check whether an action would be allowed — without executing it.

        No trace is written. Returns instantly. Use before executing
        sensitive or irreversible actions.

        Checks:

        1. Kill switch active → DENY immediately.
        2. Policy evaluation against ``action_type`` if an evaluator
           is configured.
        """
        reasons: list[str] = []

        with self._kill_switch_lock:
            ks_active = self._kill_switch_active
            ks_reason = self._kill_switch_reason or "kill switch engaged"

        if ks_active:
            reasons.append(f"kill_switch:{ks_reason}")
            return PreflightResult(
                cleared=False,
                kill_switch_active=True,
                policy_result="DENY",
                reasons=reasons,
            )

        evaluator = self.policy_evaluator
        if isinstance(evaluator, NullPolicyEvaluator):
            return PreflightResult(
                cleared=True,
                kill_switch_active=False,
                policy_result="NOT_EVALUATED",
                reasons=[],
            )

        # Run the evaluator synchronously against a minimal input.
        preview_trace = DecisionTrace(
            project=self.project,
            agent="preflight",
            inputs={"action_type": action_type},
        )
        try:
            result = asyncio.run(
                evaluator.evaluate(
                    policy_path=action_type,
                    inputs={"action_type": action_type},
                    trace=preview_trace,
                )
            )
        except Exception as exc:
            return PreflightResult(
                cleared=False,
                kill_switch_active=False,
                policy_result="DENY",
                reasons=[f"evaluator_error:{type(exc).__name__}"],
            )

        if result.result == PolicyResult.ALLOW:
            return PreflightResult(
                cleared=True,
                kill_switch_active=False,
                policy_result="ALLOW",
                reasons=[],
            )

        if result.result == PolicyResult.DENY:
            reason = result.rule_triggered or result.rationale or "policy_deny"
            return PreflightResult(
                cleared=False,
                kill_switch_active=False,
                policy_result="DENY",
                reasons=[f"policy:{reason}"],
            )

        return PreflightResult(
            cleared=False,
            kill_switch_active=False,
            policy_result=str(result.result),
            reasons=["policy_result_not_allow"],
        )

    def verify_output(
        self,
        trace_id: str,
        output: Any,
    ) -> OutputVerificationResult:
        """Retrieve a trace and verify its output hash matches ``output``.

        Fully offline. Zero network calls.
        """
        trace = self.storage.get(trace_id)
        if trace is None:
            return OutputVerificationResult(
                verified=False,
                trace_id=trace_id,
                stored_hash=None,
                computed_hash="",
                match=False,
                detail="trace not found",
            )

        if not isinstance(output, dict):
            return OutputVerificationResult(
                verified=False,
                trace_id=trace_id,
                stored_hash=trace.output_hash,
                computed_hash="",
                match=False,
                detail="output must be a dict",
            )

        computed = DecisionTrace._hash(output)
        stored = trace.output_hash
        if stored is None:
            return OutputVerificationResult(
                verified=False,
                trace_id=trace_id,
                stored_hash=None,
                computed_hash=computed,
                match=False,
                detail="trace has no output_hash recorded",
            )

        match = computed == stored
        return OutputVerificationResult(
            verified=match,
            trace_id=trace_id,
            stored_hash=stored,
            computed_hash=computed,
            match=match,
            detail="output matches recorded hash" if match else "output does not match recorded hash",
        )

    def verify_integrity(self, trace_id: str) -> IntegrityResult:
        """
        Verify a trace has not been tampered with.

        Reads the trace from storage, recomputes ``inputs_hash`` from
        the stored inputs (if present) and ``output_hash`` from the
        stored output, and compares with the stored hashes.

        This is the feature that makes Sentinel defensible in court:
        every trace can be independently verified as unmodified.

        Returns :class:`IntegrityResult` with:

          - ``verified``      — True if every hash matches
          - ``trace_id``      — the input trace id
          - ``found``         — True if the trace exists in storage
          - ``inputs_match``  — True if inputs_hash matches recomputation
          - ``output_match``  — True if output_hash matches recomputation
          - ``detail``        — human-readable explanation
        """
        trace = self.storage.get(trace_id)
        if trace is None:
            return IntegrityResult(
                verified=False,
                trace_id=trace_id,
                found=False,
                inputs_match=False,
                output_match=False,
                detail="trace not found",
            )

        stored_inputs_hash = trace.inputs_hash
        stored_output_hash = trace.output_hash

        inputs_match = True
        if trace.inputs and stored_inputs_hash:
            recomputed = DecisionTrace._hash(trace.inputs)
            inputs_match = recomputed == stored_inputs_hash

        output_match = True
        if trace.output and stored_output_hash:
            recomputed = DecisionTrace._hash(trace.output)
            output_match = recomputed == stored_output_hash

        verified = inputs_match and output_match
        if verified:
            detail = "all hashes match — trace unmodified"
        else:
            bad = []
            if not inputs_match:
                bad.append("inputs_hash")
            if not output_match:
                bad.append("output_hash")
            detail = f"hash mismatch: {', '.join(bad)}"

        return IntegrityResult(
            verified=verified,
            trace_id=trace_id,
            found=True,
            inputs_match=inputs_match,
            output_match=output_match,
            detail=detail,
        )


@dataclass
class IntegrityResult:
    """Result of a :meth:`Sentinel.verify_integrity` call."""

    verified: bool
    trace_id: str
    found: bool
    inputs_match: bool
    output_match: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "trace_id": self.trace_id,
            "found": self.found,
            "inputs_match": self.inputs_match,
            "output_match": self.output_match,
            "detail": self.detail,
        }


@dataclass
class PreflightResult:
    """Result of :meth:`Sentinel.preflight`.

    Preflight checks are advisory: no trace is written, no action is
    executed. Used to decide whether to attempt a sensitive or
    irreversible action.
    """

    cleared: bool
    kill_switch_active: bool
    policy_result: str  # "ALLOW" | "DENY" | "NOT_EVALUATED"
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cleared": self.cleared,
            "kill_switch_active": self.kill_switch_active,
            "policy_result": self.policy_result,
            "reasons": list(self.reasons),
        }


@dataclass
class OutputVerificationResult:
    """Result of :meth:`Sentinel.verify_output`."""

    verified: bool
    trace_id: str
    stored_hash: str | None
    computed_hash: str
    match: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "trace_id": self.trace_id,
            "stored_hash": self.stored_hash,
            "computed_hash": self.computed_hash,
            "match": self.match,
            "detail": self.detail,
        }


class PolicyDeniedError(Exception):
    """Raised when a policy evaluation returns DENY and no override is provided."""
    pass


class KillSwitchEngaged(Exception):
    """
    Raised when a traced call is blocked because the kill switch is engaged.

    Implements the EU AI Act Art. 14 halt mechanism: human oversight
    can stop all decisions at runtime without restart. Every blocked
    call is recorded as a DENY trace with a HumanOverride entry.
    """
    pass
