"""
sentinel.pilot
~~~~~~~~~~~~~~
Self-serve pilot state.

This module owns the contract between ``sentinel quickstart``,
``sentinel audit-gap``, and ``sentinel fix``. All three commands
read and write the same small JSON file at ``./.sentinel/config.json``
so the user's audit-readiness score moves as they close gaps.

Everything in this module is zero-network, zero-dependency, and
safe to import in air-gapped environments.
"""

from sentinel.pilot.audit_gap import (
    AuditGapReport,
    GapCategory,
    GapItem,
    compute_audit_gap,
)
from sentinel.pilot.config import (
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_DB_FILENAME,
    DEFAULT_PILOT_DIR,
    PilotConfig,
    load_pilot_config,
    save_pilot_config,
)

__all__ = [
    "DEFAULT_CONFIG_FILENAME",
    "DEFAULT_DB_FILENAME",
    "DEFAULT_PILOT_DIR",
    "PilotConfig",
    "load_pilot_config",
    "save_pilot_config",
    "AuditGapReport",
    "GapCategory",
    "GapItem",
    "compute_audit_gap",
]
