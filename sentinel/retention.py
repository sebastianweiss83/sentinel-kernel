"""Per-decision retention policy — v3.5 Item 3.

Operator-authored YAML declares how each trace is retained: full raw,
hash-only, or with specific fields redacted. Policies match on agent
name (with optional trailing ``*`` wildcard), sovereignty scope, data
residency, or tag values. First-match-wins. Defaults to v3.4.x
behaviour when no policy file is present.

See :doc:`docs/architecture/v3.5-item-3-retention-policies` for the
full design.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace

try:  # pragma: no cover - environment dependent
    import yaml as _yaml

    _HAS_YAML = True
except ImportError:  # pragma: no cover - only when PyYAML missing
    _HAS_YAML = False
    _yaml = None  # type: ignore[assignment]


_ENV_POLICY_PATH = "SENTINEL_RETENTION_POLICY"
_DEFAULT_POLICY_PATH = Path.home() / ".sentinel" / "retention-policy.yaml"
_SUPPORTED_POLICY_VERSION = 1

_ALLOWED_TOP_KEYS = {"version", "rules"}
_ALLOWED_RULE_KEYS = {"name", "match", "actions"}
_ALLOWED_MATCH_KEYS = {"agent", "sovereign_scope", "data_residency", "tags"}
_ALLOWED_ACTION_KEYS = {
    "store_inputs",
    "store_outputs",
    "retention_days",
    "redact_fields",
}


@dataclass
class RetentionAction:
    """What to do with the trace when a rule matches."""

    store_inputs: bool | None = None
    store_outputs: bool | None = None
    retention_days: int | None = None
    redact_fields: list[str] = field(default_factory=list)


@dataclass
class RetentionRule:
    """A single rule: match condition + action."""

    name: str
    match: dict[str, Any]
    actions: RetentionAction


@dataclass
class RetentionPolicy:
    """Policy loaded from YAML.

    When no file is present, :func:`load_retention_policy` returns a
    policy with an empty rule list — :meth:`match` returns None for
    every trace and the caller falls back to pre-v3.5 behaviour.
    """

    rules: list[RetentionRule] = field(default_factory=list)

    def match(self, trace: DecisionTrace) -> RetentionAction | None:
        """Return the first matching rule's action, or None."""
        for rule in self.rules:
            if _rule_matches(rule, trace):
                return rule.actions
        return None


def _agent_matches(pattern: str, agent: str) -> bool:
    if pattern.endswith("*"):
        return agent.startswith(pattern[:-1])
    return agent == pattern


def _rule_matches(rule: RetentionRule, trace: DecisionTrace) -> bool:
    m = rule.match

    if (pattern := m.get("agent")) is not None and not _agent_matches(
        pattern, trace.agent
    ):
        return False
    if (scope := m.get("sovereign_scope")) is not None and trace.sovereign_scope != scope:
        return False
    if (residency := m.get("data_residency")) is not None and trace.data_residency.value != residency:
        return False

    tag_constraints = m.get("tags") or {}
    return all(
        trace.tags.get(key) == expected
        for key, expected in tag_constraints.items()
    )


def _parse_action(raw: dict[str, Any], rule_name: str) -> RetentionAction:
    unknown = set(raw) - _ALLOWED_ACTION_KEYS
    if unknown:
        raise ValueError(
            f"rule {rule_name!r}: unknown action keys {sorted(unknown)!r}; "
            f"allowed: {sorted(_ALLOWED_ACTION_KEYS)!r}"
        )
    return RetentionAction(
        store_inputs=raw.get("store_inputs"),
        store_outputs=raw.get("store_outputs"),
        retention_days=raw.get("retention_days"),
        redact_fields=list(raw.get("redact_fields") or []),
    )


def _parse_rule(raw: dict[str, Any], index: int) -> RetentionRule:
    unknown = set(raw) - _ALLOWED_RULE_KEYS
    if unknown:
        raise ValueError(
            f"rule #{index}: unknown keys {sorted(unknown)!r}; "
            f"allowed: {sorted(_ALLOWED_RULE_KEYS)!r}"
        )
    name = str(raw.get("name") or f"rule-{index}")
    match = raw.get("match") or {}
    if not isinstance(match, dict):
        raise ValueError(
            f"rule {name!r}: match must be a dict, got {type(match).__name__}"
        )
    unknown_match = set(match) - _ALLOWED_MATCH_KEYS
    if unknown_match:
        raise ValueError(
            f"rule {name!r}: unknown match keys {sorted(unknown_match)!r}; "
            f"allowed: {sorted(_ALLOWED_MATCH_KEYS)!r}"
        )

    actions_raw = raw.get("actions") or {}
    if not isinstance(actions_raw, dict):
        raise ValueError(
            f"rule {name!r}: actions must be a dict, got "
            f"{type(actions_raw).__name__}"
        )
    actions = _parse_action(actions_raw, name)

    return RetentionRule(name=name, match=match, actions=actions)


def _parse_policy(document: dict[str, Any]) -> RetentionPolicy:
    if not isinstance(document, dict):
        raise ValueError(
            f"retention policy must be a YAML mapping, got "
            f"{type(document).__name__}"
        )
    unknown = set(document) - _ALLOWED_TOP_KEYS
    if unknown:
        raise ValueError(
            f"retention policy: unknown top-level keys {sorted(unknown)!r}; "
            f"allowed: {sorted(_ALLOWED_TOP_KEYS)!r}"
        )
    version = document.get("version")
    if version != _SUPPORTED_POLICY_VERSION:
        raise ValueError(
            f"retention policy version {version!r} is not supported; "
            f"this build supports version {_SUPPORTED_POLICY_VERSION}"
        )
    rules_raw = document.get("rules") or []
    if not isinstance(rules_raw, list):
        raise ValueError(
            f"retention policy: 'rules' must be a list, got "
            f"{type(rules_raw).__name__}"
        )
    rules = [_parse_rule(r, i) for i, r in enumerate(rules_raw)]
    return RetentionPolicy(rules=rules)


def _resolve_policy_path() -> Path | None:
    env_path = os.environ.get(_ENV_POLICY_PATH)
    if env_path:
        return Path(env_path).expanduser()
    if _DEFAULT_POLICY_PATH.exists():
        return _DEFAULT_POLICY_PATH
    return None


def load_retention_policy() -> RetentionPolicy:
    """Load the retention policy from disk, or return an empty policy.

    Resolution:

    1. ``$SENTINEL_RETENTION_POLICY`` → load YAML at that path.
    2. ``~/.sentinel/retention-policy.yaml`` → load if present.
    3. No file → empty policy (no rules, pre-v3.5 behaviour).

    Raises :class:`ValueError` on malformed YAML or unknown keys —
    fail fast, never silently no-op.

    Raises :class:`ImportError` if a policy path is configured but
    ``PyYAML`` is not available.
    """
    path = _resolve_policy_path()
    if path is None:
        return RetentionPolicy(rules=[])

    if not _HAS_YAML:  # pragma: no cover - only when PyYAML missing
        raise ImportError(
            "Retention policy requires PyYAML. Install:\n"
            "    pip install 'sentinel-kernel'"
        )

    if not path.exists():
        raise ValueError(
            f"retention policy path {path!s} set via "
            f"{_ENV_POLICY_PATH} but file does not exist"
        )

    try:
        document = _yaml.safe_load(path.read_text()) or {}
    except _yaml.YAMLError as exc:
        raise ValueError(
            f"retention policy at {path!s} is not valid YAML: {exc}"
        ) from exc

    return _parse_policy(document)


def _delete_dotted(payload: dict[str, Any], dotted_path: str) -> None:
    """Walk ``payload`` by dots, delete the leaf key. No-op if missing."""
    parts = dotted_path.split(".")
    # Policies address inputs.X or output.X; drop the top-level
    # inputs/output prefix so we can apply the remainder to the payload
    # dict passed in (which is already ``trace.inputs`` or
    # ``trace.output``).
    if parts[0] in {"inputs", "output"}:
        parts = parts[1:]
    if not parts:
        return
    cursor: Any = payload
    for part in parts[:-1]:
        if not isinstance(cursor, dict) or part not in cursor:
            return
        cursor = cursor[part]
    if isinstance(cursor, dict):
        cursor.pop(parts[-1], None)


def apply_retention_action(
    trace: DecisionTrace, action: RetentionAction
) -> None:
    """Apply ``action`` to ``trace`` in place.

    Field redaction (``redact_fields``) is applied *before* the
    store-* flags, so a rule can say "store everything but redact
    these fields" without the store-* logic first clearing the dict.
    Inputs / output hashes are never recomputed here — the originals
    already reflect the pre-redaction payload, which is what an
    integrity verifier needs.
    """
    for path in action.redact_fields:
        if path.startswith("inputs") and trace.inputs:
            _delete_dotted(trace.inputs, path)
        elif path.startswith("output") and trace.output:
            _delete_dotted(trace.output, path)

    if action.store_inputs is False:
        trace.inputs = {}
    if action.store_outputs is False:
        trace.output = {}

    if action.retention_days is not None:
        trace.tags["retention_days"] = str(action.retention_days)


__all__ = [
    "RetentionAction",
    "RetentionRule",
    "RetentionPolicy",
    "load_retention_policy",
    "apply_retention_action",
]
