"""v3.5 Item 3 — per-decision retention policies.

Covers the behaviour from ``docs/architecture/v3.5-item-3-retention-policies.md``:
YAML-defined retention rules override the constructor-level
store_inputs/store_outputs. First-match-wins. Absent policy preserves
v3.4.x behaviour. Malformed policy fails loudly at construction time.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from sentinel.core.trace import DecisionTrace
from sentinel.core.tracer import Sentinel
from sentinel.retention import (
    RetentionAction,
    RetentionPolicy,
    RetentionRule,
    _parse_policy,
    apply_retention_action,
    load_retention_policy,
)


def _write_policy(tmp_path: Path, yaml_text: str) -> Path:
    path = tmp_path / "retention.yaml"
    path.write_text(textwrap.dedent(yaml_text).strip())
    return path


# ---------------------------------------------------------------------------
# Policy parsing + loading
# ---------------------------------------------------------------------------


def test_no_policy_file_yields_empty_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SENTINEL_RETENTION_POLICY", raising=False)
    # Redirect the default path into an empty tmp_path so the user's
    # real ~/.sentinel/ file never interferes.
    from sentinel import retention

    monkeypatch.setattr(
        retention, "_DEFAULT_POLICY_PATH", tmp_path / "does-not-exist.yaml"
    )
    policy = load_retention_policy()
    assert policy.rules == []


def test_env_override_loads_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _write_policy(
        tmp_path,
        """
        version: 1
        rules:
          - name: demo
            match: { agent: demo_agent }
            actions: { store_inputs: true }
        """,
    )
    monkeypatch.setenv("SENTINEL_RETENTION_POLICY", str(path))

    policy = load_retention_policy()
    assert len(policy.rules) == 1
    assert policy.rules[0].name == "demo"
    assert policy.rules[0].actions.store_inputs is True


def test_unknown_version_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="version"):
        _parse_policy({"version": 99, "rules": []})


def test_unknown_top_key_rejected() -> None:
    with pytest.raises(ValueError, match="unknown top-level keys"):
        _parse_policy({"version": 1, "rules": [], "foo": "bar"})


def test_unknown_match_key_rejected() -> None:
    with pytest.raises(ValueError, match="unknown match keys"):
        _parse_policy(
            {
                "version": 1,
                "rules": [{"match": {"agent": "x", "bogus": "y"}, "actions": {}}],
            }
        )


def test_unknown_rule_key_rejected() -> None:
    with pytest.raises(ValueError, match="unknown keys"):
        _parse_policy(
            {
                "version": 1,
                "rules": [
                    {"match": {}, "actions": {}, "unexpected_key": 1}
                ],
            }
        )


def test_default_path_used_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no env var set, the default ``~/.sentinel/retention-policy.yaml`` is read."""
    monkeypatch.delenv("SENTINEL_RETENTION_POLICY", raising=False)
    default_path = _write_policy(
        tmp_path,
        """
        version: 1
        rules:
          - name: default-path
            match: { agent: anything_* }
            actions: { store_inputs: true }
        """,
    )
    from sentinel import retention

    monkeypatch.setattr(retention, "_DEFAULT_POLICY_PATH", default_path)

    policy = load_retention_policy()
    assert len(policy.rules) == 1
    assert policy.rules[0].name == "default-path"


def test_unknown_action_key_rejected() -> None:
    with pytest.raises(ValueError, match="unknown action keys"):
        _parse_policy(
            {
                "version": 1,
                "rules": [
                    {"match": {"agent": "x"}, "actions": {"bogus_action": True}}
                ],
            }
        )


def test_rules_list_must_be_list() -> None:
    with pytest.raises(ValueError, match="'rules' must be a list"):
        _parse_policy({"version": 1, "rules": "nope"})


def test_match_must_be_dict() -> None:
    with pytest.raises(ValueError, match="match must be a dict"):
        _parse_policy(
            {
                "version": 1,
                "rules": [{"match": "string-not-dict", "actions": {}}],
            }
        )


def test_actions_must_be_dict() -> None:
    with pytest.raises(ValueError, match="actions must be a dict"):
        _parse_policy(
            {
                "version": 1,
                "rules": [{"match": {}, "actions": "string-not-dict"}],
            }
        )


def test_top_level_must_be_mapping() -> None:
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        _parse_policy(["not", "a", "dict"])  # type: ignore[arg-type]


def test_env_path_missing_file_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(
        "SENTINEL_RETENTION_POLICY", str(tmp_path / "missing.yaml")
    )
    with pytest.raises(ValueError, match="does not exist"):
        load_retention_policy()


def test_invalid_yaml_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("{[not: valid: yaml:")
    monkeypatch.setenv("SENTINEL_RETENTION_POLICY", str(path))

    with pytest.raises(ValueError, match="not valid YAML"):
        load_retention_policy()


# ---------------------------------------------------------------------------
# Rule matching
# ---------------------------------------------------------------------------


def _trace(
    *, agent: str = "x", scope: str = "local", tags: dict[str, str] | None = None,
) -> DecisionTrace:
    from sentinel.core.trace import DataResidency

    return DecisionTrace(
        project="test",
        agent=agent,
        sovereign_scope=scope,
        data_residency=DataResidency.EU_DE,
        tags=dict(tags or {}),
    )


def test_agent_exact_match() -> None:
    policy = RetentionPolicy(
        rules=[
            RetentionRule(
                name="r",
                match={"agent": "alpha"},
                actions=RetentionAction(store_inputs=True),
            )
        ]
    )
    assert policy.match(_trace(agent="alpha")) is not None
    assert policy.match(_trace(agent="beta")) is None


def test_agent_wildcard_match() -> None:
    policy = RetentionPolicy(
        rules=[
            RetentionRule(
                name="r",
                match={"agent": "credit_*"},
                actions=RetentionAction(store_inputs=True),
            )
        ]
    )
    assert policy.match(_trace(agent="credit_decision")) is not None
    assert policy.match(_trace(agent="credit_agent")) is not None
    assert policy.match(_trace(agent="chat")) is None


def test_sovereign_scope_match() -> None:
    policy = RetentionPolicy(
        rules=[
            RetentionRule(
                name="eu-only",
                match={"sovereign_scope": "EU"},
                actions=RetentionAction(store_inputs=True),
            )
        ]
    )
    assert policy.match(_trace(scope="EU")) is not None
    assert policy.match(_trace(scope="LOCAL")) is None


def test_data_residency_match() -> None:
    from sentinel.core.trace import DataResidency

    policy = RetentionPolicy(
        rules=[
            RetentionRule(
                name="de",
                match={"data_residency": "EU-DE"},
                actions=RetentionAction(store_inputs=True),
            )
        ]
    )
    assert policy.match(_trace()) is not None  # default EU-DE in _trace
    other = _trace()
    other.data_residency = DataResidency.LOCAL
    assert policy.match(other) is None


def test_sovereign_scope_mismatch_is_skipped() -> None:
    policy = RetentionPolicy(
        rules=[
            RetentionRule(
                name="eu",
                match={"sovereign_scope": "EU"},
                actions=RetentionAction(store_inputs=True),
            )
        ]
    )
    assert policy.match(_trace(scope="LOCAL")) is None


def test_tag_match_requires_exact_value() -> None:
    policy = RetentionPolicy(
        rules=[
            RetentionRule(
                name="bafin",
                match={"tags": {"policy_family": "BaFin"}},
                actions=RetentionAction(store_inputs=True),
            )
        ]
    )
    assert policy.match(_trace(tags={"policy_family": "BaFin"})) is not None
    assert policy.match(_trace(tags={"policy_family": "internal"})) is None
    assert policy.match(_trace(tags={})) is None


def test_first_match_wins() -> None:
    policy = RetentionPolicy(
        rules=[
            RetentionRule(
                name="first",
                match={"agent": "credit_*"},
                actions=RetentionAction(store_inputs=True, retention_days=3650),
            ),
            RetentionRule(
                name="second",
                match={"agent": "credit_decision"},
                actions=RetentionAction(store_inputs=False, retention_days=30),
            ),
        ]
    )
    # "credit_decision" matches both rules; first wins.
    action = policy.match(_trace(agent="credit_decision"))
    assert action is not None
    assert action.retention_days == 3650
    assert action.store_inputs is True


# ---------------------------------------------------------------------------
# apply_retention_action
# ---------------------------------------------------------------------------


def test_apply_redact_fields_strips_leaf_keys_from_inputs() -> None:
    t = _trace()
    t.inputs = {"applicant_id": "X123", "ssn": "123-45-6789"}
    apply_retention_action(
        t, RetentionAction(store_inputs=True, redact_fields=["inputs.ssn"])
    )
    assert t.inputs == {"applicant_id": "X123"}


def test_apply_redact_fields_nested_path() -> None:
    t = _trace()
    t.output = {"decision": {"score": 0.9, "raw": "secret-raw-string"}}
    apply_retention_action(
        t,
        RetentionAction(
            store_outputs=True, redact_fields=["output.decision.raw"]
        ),
    )
    assert t.output == {"decision": {"score": 0.9}}


def test_apply_store_false_clears_inputs() -> None:
    t = _trace()
    t.inputs = {"x": 1}
    apply_retention_action(t, RetentionAction(store_inputs=False))
    assert t.inputs == {}


def test_apply_retention_days_surfaces_on_tags() -> None:
    t = _trace()
    apply_retention_action(t, RetentionAction(retention_days=3650))
    assert t.tags["retention_days"] == "3650"


def test_apply_redact_missing_key_is_noop() -> None:
    t = _trace()
    t.inputs = {"a": 1}
    # "inputs.nonexistent" doesn't exist — shouldn't crash.
    apply_retention_action(
        t, RetentionAction(store_inputs=True, redact_fields=["inputs.nonexistent.deep"])
    )
    assert t.inputs == {"a": 1}


def test_apply_store_outputs_false_clears_output() -> None:
    t = _trace()
    t.output = {"x": 1}
    apply_retention_action(t, RetentionAction(store_outputs=False))
    assert t.output == {}


def test_apply_redact_with_bare_path_noop() -> None:
    """A path with only 'inputs' (no dotted suffix) is a safe no-op."""
    t = _trace()
    t.inputs = {"a": 1}
    apply_retention_action(
        t, RetentionAction(store_inputs=True, redact_fields=["inputs"])
    )
    # The entire inputs dict shouldn't be wiped by a bare prefix.
    assert t.inputs == {"a": 1}


def test_apply_redact_unknown_prefix_is_noop() -> None:
    """A redact path that's neither inputs.* nor output.* is silently ignored."""
    t = _trace()
    t.inputs = {"a": 1}
    t.output = {"b": 2}
    apply_retention_action(
        t, RetentionAction(store_inputs=True, store_outputs=True, redact_fields=["tags.junk"])
    )
    assert t.inputs == {"a": 1}
    assert t.output == {"b": 2}


def test_apply_redact_raw_path_without_prefix() -> None:
    """A redact path with no ``inputs./output.`` prefix targets the leaf directly.

    We treat ``ssn`` as a direct key in whichever payload matches the
    first segment of the convention — but since the convention requires
    a prefix, a bare key is silently accepted by `_delete_dotted` and
    becomes a no-op at the apply layer. Covers the parts[0] non-prefix
    branch of `_delete_dotted`.
    """
    from sentinel.retention import _delete_dotted

    payload = {"ssn": "xxx"}
    # `_delete_dotted` is called with a payload and a path where parts[0]
    # is NOT 'inputs' or 'output' — the leaf is still deleted.
    _delete_dotted(payload, "ssn")
    assert payload == {}


def test_apply_redact_traversal_through_non_dict_is_noop() -> None:
    t = _trace()
    # Deliberately walk through a non-dict value in the path.
    t.inputs = {"scalar": "not-a-dict"}
    apply_retention_action(
        t,
        RetentionAction(
            store_inputs=True, redact_fields=["inputs.scalar.deeper"]
        ),
    )
    assert t.inputs == {"scalar": "not-a-dict"}


# ---------------------------------------------------------------------------
# Constructor-kwarg vs rule-action layering
# ---------------------------------------------------------------------------


def test_rule_with_only_store_inputs_falls_back_to_constructor_for_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Rule controls inputs; outputs follows Sentinel(store_outputs=...).

    Exercises the symmetric branch to
    ``test_rule_with_only_store_outputs_falls_back_to_constructor_for_inputs``.
    """
    path = _write_policy(
        tmp_path,
        """
        version: 1
        rules:
          - name: inputs-only
            match: { agent: '*' }
            actions: { store_inputs: true }
        """,
    )
    monkeypatch.setenv("SENTINEL_RETENTION_POLICY", str(path))

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace(agent_name="demo2")
    def demo(x: str) -> dict[str, str]:
        return {"r": x}

    demo("hi")
    t = s.query()[0]
    assert t.inputs != {}
    assert t.output == {}  # constructor default


def test_rule_with_only_store_outputs_falls_back_to_constructor_for_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Rule controls outputs; inputs follows Sentinel(store_inputs=...).

    Constructor default is hash-only, so when a rule sets only
    store_outputs=True, inputs are still cleared (constructor rule).
    """
    path = _write_policy(
        tmp_path,
        """
        version: 1
        rules:
          - name: outputs-only
            match: { agent: '*' }
            actions: { store_outputs: true }
        """,
    )
    monkeypatch.setenv("SENTINEL_RETENTION_POLICY", str(path))

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace(agent_name="demo")
    def demo(x: str) -> dict[str, str]:
        return {"r": x}

    demo("hello")
    t = s.query()[0]
    # Output retained (rule).
    assert t.output != {}
    # Inputs cleared (constructor default since rule didn't say).
    assert t.inputs == {}


# ---------------------------------------------------------------------------
# End-to-end integration with Sentinel._finalise_trace
# ---------------------------------------------------------------------------


def test_policy_overrides_sentinel_kwargs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """YAML-matched rule wins over Sentinel(store_inputs=False) default."""
    path = _write_policy(
        tmp_path,
        """
        version: 1
        rules:
          - name: credit-full
            match: { agent: credit_* }
            actions:
              store_inputs: true
              store_outputs: true
              retention_days: 3650
        """,
    )
    monkeypatch.setenv("SENTINEL_RETENTION_POLICY", str(path))

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace(agent_name="credit_decision")
    def credit(ssn: str) -> dict[str, Any]:
        return {"approved": True, "applicant_ssn_stored": ssn}

    credit("123-45-6789")
    t = s.query()[0]
    assert t.inputs != {}
    assert t.output != {}
    assert t.tags["retention_days"] == "3650"


def test_no_match_preserves_sentinel_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Trace that matches no rule falls through to constructor kwargs.

    Default constructor is hash-only (v3.2+ default), so inputs/output
    are empty after finalise.
    """
    path = _write_policy(
        tmp_path,
        """
        version: 1
        rules:
          - name: credit-full
            match: { agent: credit_* }
            actions: { store_inputs: true, store_outputs: true }
        """,
    )
    monkeypatch.setenv("SENTINEL_RETENTION_POLICY", str(path))

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace(agent_name="chat_agent")
    def chat(msg: str) -> dict[str, str]:
        return {"reply": "hi"}

    chat("hello")
    t = s.query()[0]
    # chat_agent matches no rule → defaults (hash-only) apply.
    assert t.inputs == {}
    assert t.output == {}
    # Hashes are still populated because _finalise_trace computes them
    # before applying the retention action / defaults.
    assert t.inputs_hash is not None
    assert t.output_hash is not None


def test_redact_fields_applies_via_finalise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _write_policy(
        tmp_path,
        """
        version: 1
        rules:
          - name: ssn-redact
            match: { agent: '*' }
            actions:
              store_inputs: true
              store_outputs: true
              redact_fields: [inputs.ssn, output.raw_score]
        """,
    )
    monkeypatch.setenv("SENTINEL_RETENTION_POLICY", str(path))

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace(agent_name="decide")
    def decide(applicant_id: str, ssn: str) -> dict[str, Any]:
        return {"approved": True, "raw_score": 0.91, "applicant": applicant_id}

    decide(applicant_id="X", ssn="123-45-6789")
    t = s.query()[0]
    assert "applicant_id" in t.inputs
    assert "ssn" not in t.inputs
    assert "approved" in t.output
    assert "raw_score" not in t.output
