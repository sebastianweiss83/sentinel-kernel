"""
tests/test_eu_ai_act_fields.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Verify that decision traces contain the fields required by
EU AI Act Article 12 (automatic logging) and Article 13 (transparency).

These tests validate real traces produced by the Sentinel kernel,
not a theoretical schema.
"""

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.core.trace import DecisionTrace, HumanOverride, PolicyResult
from sentinel.policy import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


@pytest.fixture
def sentinel_with_policy():
    def allow_all(inputs):
        return True, None

    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="eu-ai-act-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"policies/test": allow_all}),
    )


@pytest.fixture
def sentinel_no_policy():
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="eu-ai-act-test",
        data_residency=DataResidency.EU,
    )


# --- Article 12(1): Automatic logging ---

@pytest.mark.asyncio
async def test_trace_has_unique_id(sentinel_no_policy):
    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    traces = sentinel_no_policy.query(project="eu-ai-act-test")
    trace = traces[0]
    d = trace.to_dict()

    assert d["trace_id"] is not None
    assert isinstance(d["trace_id"], str)
    assert len(d["trace_id"]) > 0


@pytest.mark.asyncio
async def test_trace_has_timestamp(sentinel_no_policy):
    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    d = sentinel_no_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert d["started_at"] is not None
    assert d["completed_at"] is not None


@pytest.mark.asyncio
async def test_trace_has_agent_identity(sentinel_no_policy):
    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    d = sentinel_no_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert d["agent"] is not None
    assert d["agent"] != "unknown"


@pytest.mark.asyncio
async def test_trace_has_inputs_hash(sentinel_no_policy):
    """Art. 12: logs must capture what inputs were presented."""

    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=42)
    d = sentinel_no_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert d["inputs_hash"] is not None
    assert len(d["inputs_hash"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_trace_has_output(sentinel_no_policy):
    """Art. 12: logs must capture what was decided."""

    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"decision": "approved"}

    await decide(x=1)
    d = sentinel_no_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert d["output"] == {"decision": "approved"}


@pytest.mark.asyncio
async def test_trace_has_latency(sentinel_no_policy):
    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    d = sentinel_no_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert d["latency_ms"] is not None
    assert isinstance(d["latency_ms"], int)


# --- Article 13: Transparency (policy provenance) ---

@pytest.mark.asyncio
async def test_trace_has_policy_evaluation(sentinel_with_policy):
    @sentinel_with_policy.trace(policy="policies/test")
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    d = sentinel_with_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert d["policy"] is not None
    assert d["policy"]["policy_id"] == "policies/test"
    assert d["policy"]["result"] in ("ALLOW", "DENY", "EXCEPTION", "NOT_EVALUATED")
    assert d["policy"]["evaluator"] is not None


@pytest.mark.asyncio
async def test_trace_has_model_fields(sentinel_no_policy):
    """Art. 13: model identity must be recordable. Fields exist even if null."""

    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    d = sentinel_no_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert "model" in d
    model = d["model"]
    assert "provider" in model
    assert "name" in model
    assert "version" in model


# --- Article 14: Human oversight ---

def test_human_override_fields():
    """Art. 14: override must record who, why, and when."""
    override = HumanOverride(
        approver_id="m.schmidt@example.eu",
        approver_role="procurement-lead",
        justification="Manual review completed, budget approved by VP",
    )
    d = override.to_dict()

    assert d["approver_id"] == "m.schmidt@example.eu"
    assert d["approver_role"] == "procurement-lead"
    assert d["justification"] is not None
    assert d["approved_at"] is not None
    assert d["override_id"] is not None


# --- Data sovereignty ---

@pytest.mark.asyncio
async def test_trace_has_sovereignty_fields(sentinel_with_policy):
    @sentinel_with_policy.trace(policy="policies/test")
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    d = sentinel_with_policy.query(project="eu-ai-act-test")[0].to_dict()

    sov = d["sovereignty"]
    assert sov["data_residency"] == "EU-DE"
    assert sov["sovereign_scope"] == "EU"
    assert sov["storage_backend"] == "sqlite"


# --- Schema version ---

@pytest.mark.asyncio
async def test_trace_has_schema_version(sentinel_no_policy):
    @sentinel_no_policy.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    d = sentinel_no_policy.query(project="eu-ai-act-test")[0].to_dict()

    assert d["schema_version"] is not None
    assert d["schema_version"] == "1.0.0"


# --- from_dict() roundtrip preserves policy ---

@pytest.mark.asyncio
async def test_from_dict_preserves_policy_evaluation(sentinel_with_policy):
    """Verify from_dict() reconstructs policy_evaluation from stored JSON."""

    @sentinel_with_policy.trace(policy="policies/test")
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=1)
    traces = sentinel_with_policy.query(project="eu-ai-act-test")
    original = traces[0]

    # Roundtrip through dict
    d = original.to_dict()
    restored = DecisionTrace.from_dict(d)

    assert restored.policy_evaluation is not None
    assert restored.policy_evaluation.policy_id == "policies/test"
    assert restored.policy_evaluation.result == PolicyResult.ALLOW
