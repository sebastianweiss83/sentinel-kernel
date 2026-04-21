"""v3.5 Item 4 — write-once filesystem storage.

Covers the behaviour from ``docs/architecture/v3.5-item-4-writeonce-storage.md``:
application-layer rejection of overwrites, best-effort OS-immutable
flag application, storage_mode field propagation, and compatibility
with existing query / get semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.core.trace import DecisionTrace, PolicyResult
from sentinel.core.tracer import Sentinel
from sentinel.storage.writeonce_filesystem import (
    WriteOnceFilesystemStorage,
    WriteOnceViolation,
    _apply_immutable_flag,
    _clear_immutable_flag,
)


def _new_storage(tmp_path: Path, *, apply_immutable: bool = False) -> WriteOnceFilesystemStorage:
    """Return a fresh store — default is apply_immutable=False so tests
    can clean up tmp_path without root privileges."""
    s = WriteOnceFilesystemStorage(tmp_path / "evidence", apply_immutable=apply_immutable)
    s.initialise()
    return s


def _trace(agent: str = "demo", project: str = "wo-test") -> DecisionTrace:
    return DecisionTrace(project=project, agent=agent, inputs={"x": 1})


# ---------------------------------------------------------------------------
# Save-once semantics
# ---------------------------------------------------------------------------


def test_first_save_succeeds(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    t = _trace()
    storage.save(t)

    saved_file = (tmp_path / "evidence" / f"{t.trace_id}.ndjson")
    assert saved_file.exists()


def test_second_save_raises_writeonce_violation(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    t = _trace()
    storage.save(t)

    with pytest.raises(WriteOnceViolation) as exc_info:
        storage.save(t)

    assert exc_info.value.trace_id == t.trace_id


def test_different_traces_save_independently(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    a = _trace(agent="agent_a")
    b = _trace(agent="agent_b")
    storage.save(a)
    storage.save(b)

    assert storage.get(a.trace_id) is not None
    assert storage.get(b.trace_id) is not None


def test_invalid_trace_id_rejected(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    t = _trace()
    t.trace_id = "../../etc/passwd"

    with pytest.raises(ValueError, match="invalid trace_id"):
        storage.save(t)


def test_invalid_trace_id_on_get_returns_none(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    assert storage.get("../evil") is None


# ---------------------------------------------------------------------------
# storage_mode propagation
# ---------------------------------------------------------------------------


def test_save_sets_storage_mode_on_trace(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    t = _trace()
    assert t.storage_mode == "writeable"

    storage.save(t)

    # After save, the trace's storage_mode has been claimed.
    assert t.storage_mode == "writeonce_fs"


def test_storage_mode_persists_through_save_and_read(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    t = _trace()
    storage.save(t)

    restored = storage.get(t.trace_id)
    assert restored is not None
    assert restored.storage_mode == "writeonce_fs"


def test_storage_mode_in_serialised_json(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    t = _trace()
    storage.save(t)

    saved = tmp_path / "evidence" / f"{t.trace_id}.ndjson"
    data = json.loads(saved.read_text())
    assert data["storage_mode"] == "writeonce_fs"


# ---------------------------------------------------------------------------
# query + get compatibility
# ---------------------------------------------------------------------------


def test_query_returns_all_saved_traces(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    for i in range(3):
        t = _trace(agent=f"agent_{i}")
        storage.save(t)

    results = storage.query(project="wo-test")
    assert len(results) == 3


def test_query_filters_by_agent(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    for name in ("alpha", "beta", "alpha"):
        storage.save(_trace(agent=name))

    alphas = storage.query(agent="alpha")
    assert len(alphas) == 2


def test_query_respects_limit_and_offset(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    for i in range(5):
        storage.save(_trace(agent=f"agent_{i}"))

    limited = storage.query(project="wo-test", limit=2)
    assert len(limited) == 2

    paged = storage.query(project="wo-test", limit=2, offset=2)
    assert len(paged) == 2


def test_query_skips_corrupt_files(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    storage.save(_trace())
    (tmp_path / "evidence" / "not-a-real-trace.ndjson").write_text("{malformed}")

    # Doesn't raise; skips the corrupt file and returns the real one.
    results = storage.query(project="wo-test")
    assert len(results) == 1


def test_get_on_missing_id_returns_none(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    assert storage.get("nonexistent-trace-id") is None


def test_get_on_corrupt_file_returns_none(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    t = _trace()
    storage.save(t)
    # Can't overwrite via storage (write-once) but OS layer can corrupt
    # — we simulate a disk-level corruption.
    target = tmp_path / "evidence" / f"{t.trace_id}.ndjson"
    target.write_text("{corrupt}", encoding="utf-8")

    assert storage.get(t.trace_id) is None


def test_query_filters_by_policy_result(tmp_path: Path) -> None:
    from sentinel.core.trace import PolicyEvaluation

    storage = _new_storage(tmp_path)

    allow = _trace(agent="allow-agent")
    allow.policy_evaluation = PolicyEvaluation(
        policy_id="p", policy_version="1", result=PolicyResult.ALLOW
    )
    deny = _trace(agent="deny-agent")
    deny.policy_evaluation = PolicyEvaluation(
        policy_id="p", policy_version="1", result=PolicyResult.DENY,
        rule_triggered="r",
    )
    storage.save(allow)
    storage.save(deny)

    denies = storage.query(policy_result=PolicyResult.DENY)
    assert len(denies) == 1
    assert denies[0].policy_evaluation.result == PolicyResult.DENY


# ---------------------------------------------------------------------------
# Sentinel integration
# ---------------------------------------------------------------------------


def test_sentinel_with_writeonce_backend_e2e(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    s = Sentinel(storage=storage, signer=None)

    @s.trace
    def decide(x: str) -> dict[str, str]:
        return {"r": x}

    decide("test")

    # End-to-end: trace saved and queryable, storage_mode claimed.
    traces = s.query()
    assert len(traces) == 1
    assert traces[0].storage_mode == "writeonce_fs"


# ---------------------------------------------------------------------------
# OS-immutable flag (best-effort)
# ---------------------------------------------------------------------------


def test_apply_immutable_flag_is_best_effort(tmp_path: Path) -> None:
    """Flag application never raises — it returns True / False."""
    f = tmp_path / "test.txt"
    f.write_text("x")
    result = _apply_immutable_flag(f)
    assert isinstance(result, bool)

    # Clear before tmp_path teardown, so the fixture can delete.
    _clear_immutable_flag(f)


def test_clear_immutable_flag_is_safe_to_call_without_prior_set(
    tmp_path: Path,
) -> None:
    f = tmp_path / "unset.txt"
    f.write_text("x")
    # Never raises even if flag isn't set.
    _clear_immutable_flag(f)


def test_apply_immutable_flag_on_missing_path_silently_fails(tmp_path: Path) -> None:
    """Non-existent path — the flag call fails but we don't raise."""
    missing = tmp_path / "absent.txt"
    assert _apply_immutable_flag(missing) is False


def test_apply_immutable_flag_dispatches_chflags_on_darwin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """macOS path dispatches ``chflags uchg``. Mocks subprocess to avoid
    actually applying the flag (which would block tmp_path cleanup)."""
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(writeonce_filesystem.sys, "platform", "darwin")

    called_with: list[list[str]] = []

    def _fake_run(cmd: list[str], **_kwargs: object) -> object:
        called_with.append(cmd)

        class _Ok:
            returncode = 0
        return _Ok()

    monkeypatch.setattr(writeonce_filesystem.subprocess, "run", _fake_run)

    f = tmp_path / "x.txt"
    f.write_text("x")
    assert _apply_immutable_flag(f) is True
    assert called_with[0][0] == "chflags"
    assert "uchg" in called_with[0]


def test_apply_immutable_flag_dispatches_chattr_on_linux(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Linux path dispatches ``chattr +i``."""
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(writeonce_filesystem.sys, "platform", "linux")

    called_with: list[list[str]] = []

    def _fake_run(cmd: list[str], **_kwargs: object) -> object:
        called_with.append(cmd)

        class _Ok:
            returncode = 0
        return _Ok()

    monkeypatch.setattr(writeonce_filesystem.subprocess, "run", _fake_run)

    f = tmp_path / "x.txt"
    f.write_text("x")
    assert _apply_immutable_flag(f) is True
    assert called_with[0][0] == "chattr"
    assert "+i" in called_with[0]


def test_apply_immutable_flag_on_unsupported_platform_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows / unknown platforms: skip silently."""
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(writeonce_filesystem.sys, "platform", "win32")

    f = tmp_path / "x.txt"
    f.write_text("x")
    assert _apply_immutable_flag(f) is False


def test_clear_immutable_flag_on_darwin_invokes_chflags_nouchg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(writeonce_filesystem.sys, "platform", "darwin")
    called_with: list[list[str]] = []
    monkeypatch.setattr(
        writeonce_filesystem.subprocess,
        "run",
        lambda cmd, **_: called_with.append(cmd) or type("X", (), {"returncode": 0})(),
    )

    f = tmp_path / "x.txt"
    f.write_text("x")
    _clear_immutable_flag(f)
    assert "nouchg" in called_with[0]


def test_clear_immutable_flag_on_unsupported_platform_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows / unknown platform: clear is a silent no-op."""
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(writeonce_filesystem.sys, "platform", "win32")
    called: list[object] = []
    monkeypatch.setattr(
        writeonce_filesystem.subprocess, "run",
        lambda *a, **kw: called.append(a) or type("X", (), {"returncode": 0})(),
    )

    f = tmp_path / "x.txt"
    f.write_text("x")
    _clear_immutable_flag(f)
    assert called == []


def test_clear_immutable_flag_tolerates_subprocess_exceptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Subprocess raising (e.g., binary not found) must never bubble up."""
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(writeonce_filesystem.sys, "platform", "darwin")

    def _raise(*_a: object, **_kw: object) -> None:
        raise FileNotFoundError("chflags not on PATH")

    monkeypatch.setattr(writeonce_filesystem.subprocess, "run", _raise)

    f = tmp_path / "x.txt"
    f.write_text("x")
    # Should not raise.
    _clear_immutable_flag(f)


def test_save_with_apply_immutable_true_does_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With apply_immutable=True, save completes even if chflags fails.

    Mock subprocess so we don't actually lock the file (tmp_path cleanup
    would fail otherwise). Verifies the hot path is reached.
    """
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(
        writeonce_filesystem.subprocess,
        "run",
        lambda *_a, **_kw: type("X", (), {"returncode": 0})(),
    )

    storage = WriteOnceFilesystemStorage(tmp_path / "wo", apply_immutable=True)
    storage.initialise()
    storage.save(_trace())
    assert len(list((tmp_path / "wo").glob("*.ndjson"))) == 1


def test_query_without_project_filter_returns_every_trace(tmp_path: Path) -> None:
    """Passing no project= filter returns traces across all projects."""
    storage = _new_storage(tmp_path)
    storage.save(_trace(project="first"))
    storage.save(_trace(project="second"))

    # Do not pass project=; the filter branch is skipped.
    all_traces = storage.query()
    assert len(all_traces) == 2


def test_query_project_filter_skips_non_matching_traces(tmp_path: Path) -> None:
    storage = _new_storage(tmp_path)
    storage.save(_trace(project="kept"))
    storage.save(_trace(project="filtered-out"))

    kept = storage.query(project="kept")
    assert len(kept) == 1
    assert kept[0].project == "kept"


def test_clear_immutable_flag_on_linux_invokes_chattr_minus_i(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sentinel.storage import writeonce_filesystem

    monkeypatch.setattr(writeonce_filesystem.sys, "platform", "linux")
    called_with: list[list[str]] = []
    monkeypatch.setattr(
        writeonce_filesystem.subprocess,
        "run",
        lambda cmd, **_: called_with.append(cmd) or type("X", (), {"returncode": 0})(),
    )

    f = tmp_path / "x.txt"
    f.write_text("x")
    _clear_immutable_flag(f)
    assert "-i" in called_with[0]
