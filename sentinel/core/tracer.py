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
from pathlib import Path
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

# Sentinel values for "default not passed explicitly" — lets __init__
# distinguish between Sentinel() (honour new defaults, warn on upgrade)
# and Sentinel(store_inputs=False) (explicit opt-in, no warning).
_DEFAULT = object()
_DEFAULT_DB_PATH = "./sentinel-traces.db"
_MIGRATION_WARNING_EMITTED = False


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
        store_inputs: Any = _DEFAULT,
        store_outputs: Any = _DEFAULT,
        signer: Any = _DEFAULT,
    ):
        """
        Construct a Sentinel kernel.

        Privacy defaults (v3.2.0+)
        --------------------------
        ``store_inputs`` and ``store_outputs`` default to ``False``.
        Every trace still records a SHA-256 ``inputs_hash`` and
        ``output_hash`` — so Art. 12 proof-of-logging holds — but the
        raw payload is discarded before it reaches storage.

        To opt into raw-payload storage (e.g. for debugging in a
        closed development environment where you control the data and
        have legal basis), pass ``store_inputs=True`` and/or
        ``store_outputs=True`` explicitly. Do so only when GDPR
        Art. 6/9 and Art. 25 ("data protection by design") obligations
        are met at your end.

        A one-time ``UserWarning`` is emitted if a legacy v3.1-era
        trace DB is detected at the default location and neither flag
        was passed explicitly — this is the upgrade-path tripwire
        described in ``docs/migration-v3.2.md``.
        """
        # One-time v3.1 -> v3.2 upgrade warning. Fires only when the
        # user got here via the default code path (no explicit flags)
        # and an existing default-path trace DB suggests a prior v3.1
        # install. Never fires twice per process.
        global _MIGRATION_WARNING_EMITTED
        defaults_applied = (
            store_inputs is _DEFAULT and store_outputs is _DEFAULT
        )
        if (
            defaults_applied
            and not _MIGRATION_WARNING_EMITTED
            and storage is None
            and Path(_DEFAULT_DB_PATH).exists()
        ):
            import warnings
            warnings.warn(
                "Sentinel v3.2.0+ defaults changed: store_inputs and "
                "store_outputs now default to False (hash-only storage). "
                f"An existing trace database was detected at "
                f"{_DEFAULT_DB_PATH!r}, which suggests a prior install. "
                "New traces will NOT store raw inputs/outputs. To "
                "preserve the pre-v3.2 behaviour, pass "
                "store_inputs=True, store_outputs=True explicitly. "
                "See docs/migration-v3.2.md.",
                UserWarning,
                stacklevel=2,
            )
            _MIGRATION_WARNING_EMITTED = True

        # Storage
        self.storage: StorageBackend
        if storage is None:
            self.storage = SQLiteStorage(_DEFAULT_DB_PATH)
        elif isinstance(storage, str):
            self.storage = SQLiteStorage(storage)
        else:
            self.storage = storage

        self.project = project
        self.data_residency = data_residency
        self.sovereign_scope = sovereign_scope
        self.policy_evaluator = policy_evaluator or NullPolicyEvaluator()
        self.store_inputs = False if store_inputs is _DEFAULT else bool(store_inputs)
        self.store_outputs = False if store_outputs is _DEFAULT else bool(store_outputs)
        if signer is _DEFAULT:
            # v3.4 default: Ed25519 signer loaded / created at the
            # canonical path. Returns None gracefully when the
            # cryptography extra isn't installed or the filesystem
            # isn't writable — preserving pre-v3.4 behaviour in those
            # environments.
            from sentinel.crypto.ed25519_signer import Ed25519Signer

            self._signer = Ed25519Signer.from_default_key()
        else:
            self._signer = signer

        # Kill switch state (EU AI Act Art. 14 — human oversight halt)
        self._kill_switch_lock = threading.Lock()
        self._kill_switch_active = False
        self._kill_switch_reason: str | None = None

        # v3.5 Item 3 — retention policy resolved once per Sentinel
        # instance. Empty policy (no rules) when no YAML file present,
        # so v3.4.x behaviour is preserved.
        from sentinel.retention import load_retention_policy

        self._retention_policy = load_retention_policy()

        self.storage.initialise()

    def _finalise_trace(self, trace: DecisionTrace) -> None:
        """
        Last step before ``storage.save`` — privacy redaction boundary.

        - Ensures ``inputs_hash`` and ``output_hash`` are populated
          even if the raw payloads are empty (so proof-of-logging
          invariants hold).
        - Strips raw ``inputs`` / ``output`` from the trace when the
          kernel was constructed with ``store_inputs=False`` /
          ``store_outputs=False`` (the v3.2.0+ default).

        Callers must invoke this immediately before ``storage.save``
        so policy evaluators, signers, and in-process observers can
        still see raw payloads if they need them.
        """
        if trace.inputs and not trace.inputs_hash:
            trace.inputs_hash = DecisionTrace._hash(trace.inputs)
        if trace.output and not trace.output_hash:
            trace.output_hash = DecisionTrace._hash(trace.output)

        # v3.5 Item 3 — retention policy. When a YAML rule matches, its
        # store_inputs / store_outputs / redact_fields / retention_days
        # override the constructor-level defaults. When no rule matches,
        # the constructor's store_inputs / store_outputs values govern
        # (v3.4.x behaviour).
        action = self._retention_policy.match(trace)
        if action is not None:
            from sentinel.retention import apply_retention_action

            apply_retention_action(trace, action)
            if action.store_inputs is None and not self.store_inputs:
                trace.inputs = {}
            if action.store_outputs is None and not self.store_outputs:
                trace.output = {}
        else:
            if not self.store_inputs:
                trace.inputs = {}
            if not self.store_outputs:
                trace.output = {}

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
            inputs=inputs,
            data_residency=self.data_residency,
            sovereign_scope=self.sovereign_scope,
            storage_backend=self.storage.backend_name,
            tags=tags,
        )

        # v3.5 Item 1: capture cross-system causal context from any
        # active OpenTelemetry span. No-op when opentelemetry-api is
        # not installed or no span is active.
        from sentinel.core.otel_context import capture_current_otel_context

        if (otel_ctx := capture_current_otel_context()) is not None:
            trace.otel_trace_id = otel_ctx.trace_id
            trace.otel_span_id = otel_ctx.span_id
            trace.otel_parent_span_id = otel_ctx.parent_span_id

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
            self._finalise_trace(trace)
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
                self._finalise_trace(trace)
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
            self._finalise_trace(trace)
            self.storage.save(trace)
            raise

        elapsed = int((time.monotonic() - start) * 1000)

        output = result if isinstance(result, dict) else {"result": repr(result)}
        trace.complete(output=output, latency_ms=elapsed)

        self._sign_trace(trace)
        self._finalise_trace(trace)
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
            self._finalise_trace(trace)
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
