"""
sentinel.core.trace
~~~~~~~~~~~~~~~~~~~
The DecisionTrace is the fundamental unit of Sentinel.
Every AI decision becomes one of these.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PolicyResult(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    EXCEPTION = "EXCEPTION"
    NOT_EVALUATED = "NOT_EVALUATED"


class DataResidency(str, Enum):
    LOCAL = "local"
    EU = "EU"
    EU_DE = "EU-DE"
    EU_FR = "EU-FR"
    AIR_GAPPED = "air-gapped"


@dataclass
class PolicyEvaluation:
    """The result of evaluating a policy against a decision."""
    policy_id: str
    policy_version: str
    result: PolicyResult
    rule_triggered: str | None = None
    rationale: str | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluator: str = "sentinel-opa"

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "result": self.result.value,
            "rule_triggered": self.rule_triggered,
            "rationale": self.rationale,
            "evaluated_at": self.evaluated_at.isoformat(),
            "evaluator": self.evaluator,
        }


@dataclass
class HumanOverride:
    """Records when a human overrides a policy denial."""
    approver_id: str
    approver_role: str
    justification: str
    approved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    override_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "override_id": self.override_id,
            "approver_id": self.approver_id,
            "approver_role": self.approver_role,
            "justification": self.justification,
            "approved_at": self.approved_at.isoformat(),
        }


@dataclass
class DecisionTrace:
    """
    A structured, sovereign record of an AI decision.

    This is the fundamental unit of Sentinel. Every agent call
    that Sentinel wraps produces exactly one DecisionTrace.

    The trace answers six questions:
    - WHAT was decided?
    - WHY was it decided? (inputs + policy)
    - WHO approved it? (human-in-the-loop)
    - WHICH model ran?
    - WHERE did the data stay? (sovereignty)
    - WHEN did it happen?
    """

    # Identity
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_trace_id: str | None = None  # For chained decisions
    project: str = "default"
    agent: str = "unknown"

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    latency_ms: int | None = None

    # Decision content
    inputs: dict[str, Any] = field(default_factory=dict)
    inputs_hash: str | None = None  # SHA-256, so PII stays local
    output: dict[str, Any] = field(default_factory=dict)
    output_hash: str | None = None

    # Model
    model_provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None

    # Policy
    policy_evaluation: PolicyEvaluation | None = None
    human_override: HumanOverride | None = None

    # Sovereignty
    data_residency: DataResidency = DataResidency.LOCAL
    sovereign_scope: str = "local"
    storage_backend: str = "sqlite"

    # Context
    tags: dict[str, str] = field(default_factory=dict)
    precedent_trace_ids: list[str] = field(default_factory=list)

    # Integrity
    schema_version: str = "1.0.0"

    def __post_init__(self):
        if self.inputs and not self.inputs_hash:
            self.inputs_hash = self._hash(self.inputs)
        if self.output and not self.output_hash:
            self.output_hash = self._hash(self.output)

    @staticmethod
    def _hash(data: dict) -> str:
        serialised = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialised.encode()).hexdigest()

    def complete(self, output: dict[str, Any], latency_ms: int) -> None:
        """Mark the trace as complete with output."""
        self.completed_at = datetime.now(timezone.utc)
        self.output = output
        self.output_hash = self._hash(output)
        self.latency_ms = latency_ms

    def add_override(self, override: HumanOverride) -> None:
        """Record a human override of a policy denial."""
        self.human_override = override
        if self.policy_evaluation:
            self.policy_evaluation.result = PolicyResult.EXCEPTION

    def link_precedent(self, trace_id: str) -> None:
        """Link this decision to a prior decision that set precedent."""
        if trace_id not in self.precedent_trace_ids:
            self.precedent_trace_ids.append(trace_id)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "parent_trace_id": self.parent_trace_id,
            "project": self.project,
            "agent": self.agent,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "latency_ms": self.latency_ms,
            "inputs_hash": self.inputs_hash,
            "inputs": self.inputs,
            "output": self.output,
            "output_hash": self.output_hash,
            "model": {
                "provider": self.model_provider,
                "name": self.model_name,
                "version": self.model_version,
                "tokens_input": self.tokens_input,
                "tokens_output": self.tokens_output,
            },
            "policy": self.policy_evaluation.to_dict() if self.policy_evaluation else None,
            "human_override": self.human_override.to_dict() if self.human_override else None,
            "sovereignty": {
                "data_residency": self.data_residency.value,
                "sovereign_scope": self.sovereign_scope,
                "storage_backend": self.storage_backend,
            },
            "tags": self.tags,
            "precedent_trace_ids": self.precedent_trace_ids,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionTrace":
        trace = cls(
            trace_id=data["trace_id"],
            parent_trace_id=data.get("parent_trace_id"),
            project=data.get("project", "default"),
            agent=data.get("agent", "unknown"),
            inputs=data.get("inputs", {}),
            inputs_hash=data.get("inputs_hash"),
            output=data.get("output", {}),
            output_hash=data.get("output_hash"),
            tags=data.get("tags", {}),
            precedent_trace_ids=data.get("precedent_trace_ids", []),
            schema_version=data.get("schema_version", "1.0.0"),
        )

        trace.latency_ms = data.get("latency_ms")
        if started := data.get("started_at"):
            from datetime import datetime, timezone
            trace.started_at = datetime.fromisoformat(started)
        if completed := data.get("completed_at"):
            from datetime import datetime, timezone
            trace.completed_at = datetime.fromisoformat(completed)

        if model := data.get("model"):
            trace.model_provider = model.get("provider")
            trace.model_name = model.get("name")
            trace.model_version = model.get("version")
            trace.tokens_input = model.get("tokens_input")
            trace.tokens_output = model.get("tokens_output")

        if sov := data.get("sovereignty"):
            trace.data_residency = DataResidency(sov.get("data_residency", "local"))
            trace.sovereign_scope = sov.get("sovereign_scope", "local")
            trace.storage_backend = sov.get("storage_backend", "sqlite")

        return trace
