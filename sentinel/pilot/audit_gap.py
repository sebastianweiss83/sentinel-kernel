"""
sentinel.pilot.audit_gap
~~~~~~~~~~~~~~~~~~~~~~~~
The audit-readiness scoring engine.

Deterministic, transparent, and deliberately honest. The score is
computed from two inputs:

1. the pilot config at ``./.sentinel/config.json``
2. the trace storage at ``./.sentinel/traces.db`` (or whatever the
   config points at)

Design principles
-----------------
- **Honest weighting.** Categories total exactly 100. Every check is
  enumerable in :data:`CATEGORIES`. A user reading the source should
  be able to predict the score from their state.
- **Three buckets.** Library / deployment / organisational. The
  bucket a gap lives in determines how it can be closed — and
  implicitly, whether the user can close it alone or needs help.
- **No hidden telemetry.** The engine writes nothing, phones nothing,
  and takes no network. It is pure computation over two files.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from sentinel.pilot.config import (
    PilotConfig,
)

if TYPE_CHECKING:  # pragma: no cover
    pass


class GapCategory(Enum):
    """Where a gap lives — determines how it gets closed."""

    LIBRARY = "library"  # Sentinel can close this with `sentinel fix ...`
    DEPLOYMENT = "deployment"  # User must make a deployment decision
    ORGANISATIONAL = "organisational"  # Human authorship required


@dataclass(frozen=True)
class CategoryCheck:
    """One scored category in the audit-gap report."""

    key: str
    label: str
    weight: int
    bucket: GapCategory
    fix_hint: str | None = None  # e.g. "sentinel fix kill-switch"
    article_ref: str | None = None  # e.g. "Art. 14"


CATEGORIES: tuple[CategoryCheck, ...] = (
    # --- always-on library categories (close automatically at quickstart) ---
    CategoryCheck(
        key="art12_logging",
        label="Art. 12   Automatic logging",
        weight=20,
        bucket=GapCategory.LIBRARY,
        article_ref="Art. 12",
    ),
    CategoryCheck(
        key="art13_transparency",
        label="Art. 13   Transparency metadata",
        weight=10,
        bucket=GapCategory.LIBRARY,
        article_ref="Art. 13",
    ),
    CategoryCheck(
        key="art17_quality_record",
        label="Art. 17   Quality management record",
        weight=10,
        bucket=GapCategory.LIBRARY,
        article_ref="Art. 17",
    ),
    CategoryCheck(
        key="data_residency_declared",
        label="Data residency declared",
        weight=10,
        bucket=GapCategory.LIBRARY,
    ),
    CategoryCheck(
        key="offline_verified",
        label="Offline / air-gapped storage",
        weight=10,
        bucket=GapCategory.LIBRARY,
    ),
    # --- library gaps the user closes via `sentinel fix` --------------------
    CategoryCheck(
        key="art14_kill_switch",
        label="Art. 14   Human oversight (kill switch)",
        weight=10,
        bucket=GapCategory.LIBRARY,
        fix_hint="sentinel fix kill-switch",
        article_ref="Art. 14",
    ),
    CategoryCheck(
        key="retention_policy",
        label="Retention policy",
        weight=10,
        bucket=GapCategory.LIBRARY,
        fix_hint="sentinel fix retention --days 2555",
    ),
    # --- deployment gaps (user must decide) ---------------------------------
    CategoryCheck(
        key="long_lived_signing_key",
        label="Auditor-grade signing key",
        weight=10,
        bucket=GapCategory.DEPLOYMENT,
    ),
    CategoryCheck(
        key="production_backend",
        label="Production storage backend",
        weight=5,
        bucket=GapCategory.DEPLOYMENT,
    ),
    # --- organisational gaps (human authorship) -----------------------------
    CategoryCheck(
        key="annex_iv_documentation",
        label="Art. 11   Annex IV technical documentation",
        weight=5,
        bucket=GapCategory.ORGANISATIONAL,
        article_ref="Art. 11",
    ),
)

TOTAL_WEIGHT = sum(c.weight for c in CATEGORIES)
assert TOTAL_WEIGHT == 100, "audit-gap category weights must total 100"


@dataclass(frozen=True)
class GapItem:
    """One line in the audit-gap report."""

    key: str
    label: str
    status: str  # "complete" | "partial" | "missing"
    detail: str
    weight: int
    points_awarded: int
    bucket: GapCategory
    fix_hint: str | None
    article_ref: str | None


@dataclass(frozen=True)
class AuditGapReport:
    """
    The full audit-gap scorecard.

    Construct via :func:`compute_audit_gap`. All fields are precomputed
    for both text and JSON rendering.
    """

    score: int  # 0..100
    items: tuple[GapItem, ...]
    trace_count: int
    config_present: bool
    storage_path: str
    profile: str = "default"

    @property
    def library_gaps(self) -> list[GapItem]:
        return [
            item
            for item in self.items
            if item.bucket == GapCategory.LIBRARY and item.status != "complete"
        ]

    @property
    def deployment_gaps(self) -> list[GapItem]:
        return [
            item
            for item in self.items
            if item.bucket == GapCategory.DEPLOYMENT and item.status != "complete"
        ]

    @property
    def organisational_gaps(self) -> list[GapItem]:
        return [
            item
            for item in self.items
            if item.bucket == GapCategory.ORGANISATIONAL and item.status != "complete"
        ]

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "profile": self.profile,
            "trace_count": self.trace_count,
            "config_present": self.config_present,
            "storage_path": self.storage_path,
            "items": [
                {
                    "key": item.key,
                    "label": item.label,
                    "status": item.status,
                    "detail": item.detail,
                    "weight": item.weight,
                    "points_awarded": item.points_awarded,
                    "bucket": item.bucket.value,
                    "fix_hint": item.fix_hint,
                    "article_ref": item.article_ref,
                }
                for item in self.items
            ],
            "gaps": {
                "library": [g.key for g in self.library_gaps],
                "deployment": [g.key for g in self.deployment_gaps],
                "organisational": [g.key for g in self.organisational_gaps],
            },
            "contact": {
                "url": "https://sentinel-kernel.eu/pilot",
                "copy": "30-minute call. No slides. No sales.",
                "required": False,
            },
        }


def compute_audit_gap(
    config: PilotConfig | None,
    trace_count: int,
    storage_path: str,
    profile: str = "default",
) -> AuditGapReport:
    """
    Compute the audit-gap score from a pilot config and a trace count.

    This function is pure — no file reads, no network, no imports
    outside the pilot package. Callers pass in everything it needs.

    ``config`` may be ``None`` if the user has never run
    ``sentinel quickstart`` — in that case we still score what we
    can (storage path, residency default) and mark the rest missing.
    """
    has_storage = trace_count > 0
    cfg = config  # alias for brevity

    items: list[GapItem] = []

    for category in CATEGORIES:
        awarded, status, detail = _score_category(
            category,
            cfg=cfg,
            has_storage=has_storage,
            trace_count=trace_count,
            storage_path=storage_path,
        )
        items.append(
            GapItem(
                key=category.key,
                label=category.label,
                status=status,
                detail=detail,
                weight=category.weight,
                points_awarded=awarded,
                bucket=category.bucket,
                fix_hint=category.fix_hint,
                article_ref=category.article_ref,
            )
        )

    total = sum(i.points_awarded for i in items)
    return AuditGapReport(
        score=total,
        items=tuple(items),
        trace_count=trace_count,
        config_present=cfg is not None,
        storage_path=storage_path,
        profile=profile,
    )


def _score_category(
    category: CategoryCheck,
    *,
    cfg: PilotConfig | None,
    has_storage: bool,
    trace_count: int,
    storage_path: str,
) -> tuple[int, str, str]:
    """Return ``(points_awarded, status, detail)`` for one category."""
    key = category.key
    weight = category.weight

    # --- Art. 12: automatic logging -----------------------------------------
    if key == "art12_logging":
        if has_storage:
            return weight, "complete", f"{trace_count} traces recorded"
        return 0, "missing", "no traces yet — run your instrumented code once"

    # --- Art. 13: transparency metadata -------------------------------------
    if key == "art13_transparency":
        if has_storage:
            return weight, "complete", "agent, model, policy fields populated"
        return 0, "missing", "no traces yet"

    # --- Art. 17: quality management record ---------------------------------
    if key == "art17_quality_record":
        if has_storage:
            return weight, "complete", "append-only record present"
        return 0, "missing", "no traces yet"

    # --- Data residency declared --------------------------------------------
    if key == "data_residency_declared":
        scope = (cfg.sovereign_scope if cfg else "").upper()
        residency = (cfg.data_residency if cfg else "").upper()
        if scope in {"EU", "LOCAL"} and residency:
            return weight, "complete", f"{scope} — {residency}"
        return 0, "missing", "run: sentinel quickstart"

    # --- Offline / air-gapped storage ---------------------------------------
    if key == "offline_verified":
        # Local filesystem path counts as offline-verified, but only
        # when the user has actually declared a pilot (no config =
        # nothing has happened yet, so the score stays at zero).
        if cfg is None:
            return 0, "missing", "run: sentinel quickstart"
        is_local = "://" not in storage_path and not storage_path.startswith(
            ("http", "https", "s3", "gs")
        )
        if is_local:
            return weight, "complete", f"local filesystem at {storage_path}"
        return 0, "missing", "remote backend detected"

    # --- Art. 14: kill switch -----------------------------------------------
    if key == "art14_kill_switch":
        if cfg and cfg.kill_switch.registered:
            return weight, "complete", "kill switch handler registered"
        return 0, "missing", "no kill switch registered"

    # --- Retention policy ----------------------------------------------------
    if key == "retention_policy":
        if cfg and cfg.retention.days is not None:
            return weight, "complete", f"{cfg.retention.days} days"
        return 0, "missing", "not configured"

    # --- Auditor-grade signing key -------------------------------------------
    if key == "long_lived_signing_key":
        if cfg and cfg.signing.key_type == "long_lived":
            return weight, "complete", "long-lived key provisioned"
        return 0, "missing", "ephemeral demo key in use"

    # --- Production storage backend ------------------------------------------
    if key == "production_backend":
        if cfg and cfg.production_backend:
            return weight, "complete", "production backend declared"
        # Partial credit when the user is clearly in pilot mode — they
        # get 0 now, not a misleading half-score.
        return 0, "missing", f"using local SQLite at {storage_path}"

    # --- Annex IV technical documentation -----------------------------------
    if key == "annex_iv_documentation":
        if cfg and cfg.annex_iv_doc_path:
            path_exists = Path(cfg.annex_iv_doc_path).exists()
            if path_exists:
                return weight, "complete", cfg.annex_iv_doc_path
            return 0, "missing", f"linked but file missing: {cfg.annex_iv_doc_path}"
        return 0, "missing", "requires human authorship (Annex IV)"

    # Unknown category — should never happen unless CATEGORIES is edited
    # without updating this switch. Fail loudly in tests, silently in prod.
    return 0, "missing", f"unknown category: {key}"  # pragma: no cover
