"""
sentinel.pilot.config
~~~~~~~~~~~~~~~~~~~~~
Small JSON-backed config for the self-serve pilot.

This file is the source of truth for ``sentinel audit-gap``. It
records decisions the user has made (retention, kill switch, signing
key type, production backend, Annex IV doc path) that are not
derivable from the trace storage alone.

Design notes
------------
- **No third-party dependencies.** We use stdlib ``json`` so this
  works in air-gapped environments and under ``pipx`` without extras.
- **Immutability.** Every update returns a new ``PilotConfig`` — we
  never mutate in place. Callers save explicitly.
- **Forward compatibility.** Unknown keys are preserved round-trip so
  older CLIs do not drop data written by newer ones.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_PILOT_DIR = ".sentinel"
DEFAULT_CONFIG_FILENAME = "config.json"
DEFAULT_DB_FILENAME = "traces.db"

PILOT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class KillSwitchConfig:
    registered: bool = False
    handler_path: str | None = None
    last_tested_at: str | None = None


@dataclass(frozen=True)
class RetentionConfig:
    days: int | None = None
    policy_name: str | None = None


@dataclass(frozen=True)
class SigningConfig:
    key_type: str = "ephemeral"  # "ephemeral" | "long_lived"
    key_path: str | None = None


@dataclass(frozen=True)
class PilotConfig:
    """
    Persistent state for the self-serve pilot experience.

    Construct new instances via ``replace(config, field=value)``; never
    mutate. Save via :func:`save_pilot_config`.
    """

    schema_version: str = PILOT_SCHEMA_VERSION
    created_at: str = ""
    updated_at: str = ""
    project: str = "sentinel-pilot"
    storage_path: str = f"./{DEFAULT_PILOT_DIR}/{DEFAULT_DB_FILENAME}"
    data_residency: str = "LOCAL"
    sovereign_scope: str = "EU"
    kill_switch: KillSwitchConfig = field(default_factory=KillSwitchConfig)
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    signing: SigningConfig = field(default_factory=SigningConfig)
    annex_iv_doc_path: str | None = None
    production_backend: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def with_timestamps(self) -> PilotConfig:
        """Return a copy with ``updated_at`` set to now. Used on save."""
        now = datetime.now(UTC).isoformat(timespec="seconds")
        created = self.created_at or now
        return replace(self, created_at=created, updated_at=now)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        # Flatten the ``extra`` bag on save so forward-compat keys
        # live at the top level where the JSON reader expects them.
        extra = raw.pop("extra", {}) or {}
        merged = {**extra, **raw}
        return merged


def default_pilot_paths(base: Path | str | None = None) -> tuple[Path, Path, Path]:
    """
    Return ``(pilot_dir, config_path, db_path)`` for the given base.

    ``base`` defaults to the current working directory. All paths are
    resolved to absolutes.
    """
    base_path = Path(base) if base is not None else Path.cwd()
    pilot_dir = (base_path / DEFAULT_PILOT_DIR).resolve()
    config_path = pilot_dir / DEFAULT_CONFIG_FILENAME
    db_path = pilot_dir / DEFAULT_DB_FILENAME
    return pilot_dir, config_path, db_path


def load_pilot_config(path: Path | str | None = None) -> PilotConfig | None:
    """
    Load a PilotConfig from ``path`` (or the default location).

    Returns ``None`` if the file does not exist. Raises ``ValueError``
    if the file exists but is not valid JSON, so callers can surface
    a helpful error instead of failing silently.
    """
    target = Path(path) if path is not None else default_pilot_paths()[1]
    if not target.exists():
        return None

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"pilot config at {target} is not valid JSON: {exc.msg}"
        ) from exc

    return _from_dict(raw)


def save_pilot_config(
    config: PilotConfig,
    path: Path | str | None = None,
) -> Path:
    """
    Persist a PilotConfig to ``path`` (or the default location).

    Creates the parent directory if missing. Stamps ``updated_at``
    automatically. Returns the path written.
    """
    target = Path(path) if path is not None else default_pilot_paths()[1]
    target.parent.mkdir(parents=True, exist_ok=True)

    stamped = config.with_timestamps()
    target.write_text(
        json.dumps(stamped.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def _from_dict(raw: dict[str, Any]) -> PilotConfig:
    """
    Build a PilotConfig from a JSON dict, preserving unknown keys in
    ``extra`` so forward-compat data is not lost on round-trip.
    """
    known_fields = {
        "schema_version",
        "created_at",
        "updated_at",
        "project",
        "storage_path",
        "data_residency",
        "sovereign_scope",
        "kill_switch",
        "retention",
        "signing",
        "annex_iv_doc_path",
        "production_backend",
    }
    extra = {k: v for k, v in raw.items() if k not in known_fields}

    kill_switch_raw = raw.get("kill_switch") or {}
    retention_raw = raw.get("retention") or {}
    signing_raw = raw.get("signing") or {}

    return PilotConfig(
        schema_version=str(raw.get("schema_version", PILOT_SCHEMA_VERSION)),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
        project=str(raw.get("project", "sentinel-pilot")),
        storage_path=str(
            raw.get("storage_path", f"./{DEFAULT_PILOT_DIR}/{DEFAULT_DB_FILENAME}")
        ),
        data_residency=str(raw.get("data_residency", "LOCAL")),
        sovereign_scope=str(raw.get("sovereign_scope", "EU")),
        kill_switch=KillSwitchConfig(
            registered=bool(kill_switch_raw.get("registered", False)),
            handler_path=kill_switch_raw.get("handler_path"),
            last_tested_at=kill_switch_raw.get("last_tested_at"),
        ),
        retention=RetentionConfig(
            days=(
                int(retention_raw["days"])
                if retention_raw.get("days") is not None
                else None
            ),
            policy_name=retention_raw.get("policy_name"),
        ),
        signing=SigningConfig(
            key_type=str(signing_raw.get("key_type", "ephemeral")),
            key_path=signing_raw.get("key_path"),
        ),
        annex_iv_doc_path=raw.get("annex_iv_doc_path"),
        production_backend=bool(raw.get("production_backend", False)),
        extra=extra,
    )
