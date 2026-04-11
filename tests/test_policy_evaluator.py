"""
tests/test_policy_evaluator.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the three built-in policy evaluators:
  - NullPolicyEvaluator        — default, allows everything
  - LocalRegoEvaluator         — shells out to OPA binary
  - SimpleRuleEvaluator        — in-process Python callables

LocalRegoEvaluator tests mock asyncio.create_subprocess_exec so that
the tests do not require OPA to be installed and never hit the network.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sentinel.core.trace import DecisionTrace, PolicyResult
from sentinel.policy.evaluator import (
    LocalRegoEvaluator,
    NullPolicyEvaluator,
    SimpleRuleEvaluator,
)


def _trace() -> DecisionTrace:
    return DecisionTrace(project="test", agent="unit-test")


# ---------------------------------------------------------------------------
# NullPolicyEvaluator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_null_policy_returns_not_evaluated() -> None:
    ev = NullPolicyEvaluator()
    result = await ev.evaluate("some/path", {"a": 1}, _trace())
    assert result.result == PolicyResult.NOT_EVALUATED
    assert result.policy_id == "some/path"
    assert result.policy_version == "null"
    assert "No policy evaluator" in (result.rationale or "")


# ---------------------------------------------------------------------------
# SimpleRuleEvaluator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simple_rule_allow() -> None:
    def rule(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    ev = SimpleRuleEvaluator({"allow.py": rule})
    result = await ev.evaluate("allow.py", {"x": 1}, _trace())
    assert result.result == PolicyResult.ALLOW
    assert result.rule_triggered is None
    assert result.evaluator == "sentinel-simple"
    assert result.policy_version == "python-callable"


@pytest.mark.asyncio
async def test_simple_rule_deny_with_rule_name() -> None:
    def rule(inputs: dict) -> tuple[bool, str | None]:
        return False, "too_large"

    ev = SimpleRuleEvaluator({"threshold.py": rule})
    result = await ev.evaluate("threshold.py", {"amount": 9999}, _trace())
    assert result.result == PolicyResult.DENY
    assert result.rule_triggered == "too_large"


@pytest.mark.asyncio
async def test_simple_rule_missing_key_raises_keyerror() -> None:
    ev = SimpleRuleEvaluator({"known.py": lambda _i: (True, None)})
    with pytest.raises(KeyError, match="No rule registered"):
        await ev.evaluate("unknown.py", {}, _trace())


# ---------------------------------------------------------------------------
# LocalRegoEvaluator
# ---------------------------------------------------------------------------


def _opa_stdout(payload: dict) -> bytes:
    # OPA eval output format: {"result": [{"expressions": [{"value": ...}]}]}
    return json.dumps(
        {"result": [{"expressions": [{"value": payload}]}]}
    ).encode()


def _fake_proc(returncode: int, stdout: bytes = b"", stderr: bytes = b""):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


def test_local_rego_init_default_binary() -> None:
    ev = LocalRegoEvaluator()
    assert ev.opa_binary == "opa"


def test_local_rego_init_custom_binary() -> None:
    ev = LocalRegoEvaluator(opa_binary="/opt/opa/bin/opa")
    assert ev.opa_binary == "/opt/opa/bin/opa"


@pytest.mark.asyncio
async def test_local_rego_rejects_path_traversal(tmp_path: Path) -> None:
    ev = LocalRegoEvaluator()
    with pytest.raises(ValueError, match="must not contain"):
        await ev.evaluate("../evil.rego", {}, _trace())


@pytest.mark.asyncio
async def test_local_rego_missing_policy_file_raises(tmp_path: Path) -> None:
    ev = LocalRegoEvaluator()
    missing = tmp_path / "does_not_exist.rego"
    with pytest.raises(FileNotFoundError):
        await ev.evaluate(str(missing), {}, _trace())


@pytest.mark.asyncio
async def test_local_rego_allow_path(tmp_path: Path) -> None:
    policy = tmp_path / "policy.rego"
    policy.write_text(
        "package sentinel\nallow := true\n", encoding="utf-8"
    )
    ev = LocalRegoEvaluator()
    fake = _fake_proc(0, _opa_stdout({"allow": True}))

    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=fake)
    ):
        result = await ev.evaluate(str(policy), {"req": "go"}, _trace())

    assert result.result == PolicyResult.ALLOW
    assert result.evaluator == "opa-local"
    assert result.policy_id == str(policy)
    # version is derived from file hash — should be 12 hex chars
    assert len(result.policy_version) == 12
    assert all(c in "0123456789abcdef" for c in result.policy_version)


@pytest.mark.asyncio
async def test_local_rego_deny_path_captures_reason(tmp_path: Path) -> None:
    policy = tmp_path / "policy.rego"
    policy.write_text(
        "package sentinel\nallow := false\n", encoding="utf-8"
    )
    ev = LocalRegoEvaluator()
    fake = _fake_proc(
        0, _opa_stdout({"allow": False, "deny_reason": "insufficient_role"})
    )

    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=fake)
    ):
        result = await ev.evaluate(str(policy), {"role": "guest"}, _trace())

    assert result.result == PolicyResult.DENY
    assert result.rule_triggered == "insufficient_role"


@pytest.mark.asyncio
async def test_local_rego_nonzero_exit_raises(tmp_path: Path) -> None:
    policy = tmp_path / "policy.rego"
    policy.write_text("package sentinel\n", encoding="utf-8")
    ev = LocalRegoEvaluator()
    fake = _fake_proc(1, b"", b"parse error: unexpected token")

    with patch(
        "asyncio.create_subprocess_exec", AsyncMock(return_value=fake)
    ), pytest.raises(RuntimeError, match="OPA evaluation failed"):
        await ev.evaluate(str(policy), {}, _trace())


@pytest.mark.asyncio
async def test_local_rego_cleanup_removes_temp_file_on_success(
    tmp_path: Path,
) -> None:
    policy = tmp_path / "policy.rego"
    policy.write_text("package sentinel\nallow := true\n", encoding="utf-8")
    ev = LocalRegoEvaluator()
    fake = _fake_proc(0, _opa_stdout({"allow": True}))

    captured_input_file: list[str] = []

    original = asyncio.create_subprocess_exec

    async def spy(*args, **kwargs):  # noqa: ANN001
        # args: (opa, "eval", "--data", policy, "--input", input_file, ...)
        for i, a in enumerate(args):
            if a == "--input":
                captured_input_file.append(args[i + 1])
        return fake

    with patch("asyncio.create_subprocess_exec", side_effect=spy):
        await ev.evaluate(str(policy), {"k": "v"}, _trace())

    assert captured_input_file
    # Temp file should have been cleaned up after evaluation
    assert not Path(captured_input_file[0]).exists()
    # Silence unused-variable warning for `original`
    del original


def test_get_policy_version_is_deterministic(tmp_path: Path) -> None:
    policy = tmp_path / "a.rego"
    policy.write_text("package s\nallow := true\n", encoding="utf-8")
    v1 = LocalRegoEvaluator._get_policy_version(policy)
    v2 = LocalRegoEvaluator._get_policy_version(policy)
    assert v1 == v2
    assert len(v1) == 12


def test_get_policy_version_changes_with_content(tmp_path: Path) -> None:
    a = tmp_path / "a.rego"
    b = tmp_path / "b.rego"
    a.write_text("package s\nallow := true\n", encoding="utf-8")
    b.write_text("package s\nallow := false\n", encoding="utf-8")
    assert LocalRegoEvaluator._get_policy_version(
        a
    ) != LocalRegoEvaluator._get_policy_version(b)
