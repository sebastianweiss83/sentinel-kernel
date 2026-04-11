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
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from sentinel.core.trace import DataResidency, DecisionTrace, PolicyResult
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

        self.storage.initialise()

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
            self.storage.save(trace)
            raise

        elapsed = int((time.monotonic() - start) * 1000)

        output = result if isinstance(result, dict) else {"result": repr(result)}
        trace.complete(
            output=output if self.store_outputs else {},
            latency_ms=elapsed,
        )

        self.storage.save(trace)
        return result

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


class PolicyDeniedError(Exception):
    """Raised when a policy evaluation returns DENY and no override is provided."""
    pass
