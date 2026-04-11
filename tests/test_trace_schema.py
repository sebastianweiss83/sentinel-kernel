"""
tests/test_trace_schema.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for DecisionTrace schema correctness.

Covers: field presence, to_dict() structure, from_dict() roundtrip,
inputs_hash auto-computation, and complete() side effects.
"""

import hashlib
import json
from datetime import datetime

from sentinel.core.trace import DataResidency, DecisionTrace


def test_trace_creation_has_required_fields():
    trace = DecisionTrace(project="test-project", agent="test-agent")

    assert trace.trace_id is not None
    assert len(trace.trace_id) == 36  # UUID4 string length

    assert trace.started_at is not None
    assert isinstance(trace.started_at, datetime)

    assert trace.schema_version == "1.0.0"

    # inputs_hash is None when inputs is empty (no hash computed for empty dict)
    # But when inputs are provided it must be set
    trace_with_inputs = DecisionTrace(
        project="test-project",
        agent="test-agent",
        inputs={"key": "value"},
    )
    assert trace_with_inputs.inputs_hash is not None


def test_trace_creation_inputs_hash_auto_computed():
    inputs = {"amount": 500, "currency": "EUR"}
    trace = DecisionTrace(inputs=inputs)

    expected = hashlib.sha256(
        json.dumps(inputs, sort_keys=True, default=str).encode()
    ).hexdigest()

    assert trace.inputs_hash == expected


def test_to_dict_produces_correct_structure():
    trace = DecisionTrace(
        project="sentinel-tests",
        agent="schema-checker",
        inputs={"x": 1},
    )

    d = trace.to_dict()

    # Top-level required keys
    expected_keys = {
        "schema_version",
        "trace_id",
        "parent_trace_id",
        "project",
        "agent",
        "started_at",
        "completed_at",
        "latency_ms",
        "inputs_hash",
        "inputs",
        "output",
        "output_hash",
        "model",
        "policy",
        "human_override",
        "sovereignty",
        "tags",
        "precedent_trace_ids",
    }
    assert expected_keys == set(d.keys())

    # Nested structures
    assert set(d["model"].keys()) == {"provider", "name", "version", "tokens_input", "tokens_output"}
    assert set(d["sovereignty"].keys()) == {"data_residency", "sovereign_scope", "storage_backend"}

    assert d["project"] == "sentinel-tests"
    assert d["agent"] == "schema-checker"
    assert d["schema_version"] == "1.0.0"
    assert d["inputs_hash"] is not None


def test_from_dict_roundtrip():
    original = DecisionTrace(
        project="roundtrip-project",
        agent="roundtrip-agent",
        inputs={"msg": "hello"},
        tags={"env": "test"},
        data_residency=DataResidency.EU_DE,
    )
    original.complete(output={"result": "ok"}, latency_ms=42)

    restored = DecisionTrace.from_dict(original.to_dict())

    assert restored.trace_id == original.trace_id
    assert restored.project == original.project
    assert restored.agent == original.agent
    assert restored.inputs == original.inputs
    assert restored.inputs_hash == original.inputs_hash
    assert restored.output == original.output
    assert restored.output_hash == original.output_hash
    assert restored.latency_ms == original.latency_ms
    assert restored.tags == original.tags
    assert restored.data_residency == DataResidency.EU_DE
    assert restored.schema_version == original.schema_version


def test_complete_sets_completed_at_and_latency_ms():
    trace = DecisionTrace(project="test", agent="timer")
    assert trace.completed_at is None
    assert trace.latency_ms is None

    trace.complete(output={"value": 99}, latency_ms=123)

    assert trace.completed_at is not None
    assert isinstance(trace.completed_at, datetime)
    assert trace.latency_ms == 123
    assert trace.output == {"value": 99}
    assert trace.output_hash is not None


def test_inputs_hash_is_sha256():
    inputs = {"key": "value", "number": 42}
    trace = DecisionTrace(inputs=inputs)

    serialised = json.dumps(inputs, sort_keys=True, default=str).encode()
    expected = hashlib.sha256(serialised).hexdigest()

    assert trace.inputs_hash == expected
    assert len(trace.inputs_hash) == 64  # SHA-256 hex digest length


def test_to_json_is_valid_json():
    trace = DecisionTrace(project="json-test", agent="json-agent", inputs={"q": 1})
    json_str = trace.to_json()
    parsed = json.loads(json_str)
    assert parsed["trace_id"] == trace.trace_id


def test_default_data_residency_is_local():
    trace = DecisionTrace()
    assert trace.data_residency == DataResidency.LOCAL


def test_parent_trace_id_defaults_none():
    trace = DecisionTrace()
    assert trace.parent_trace_id is None
    d = trace.to_dict()
    assert d["parent_trace_id"] is None
