"""
sentinel.pilot.render
~~~~~~~~~~~~~~~~~~~~~
Text rendering for ``sentinel audit-gap``.

Kept separate from the scoring engine so the renderer can be tested
and iterated without touching the logic. Tone principles:

- calm, audit-like, terse
- never congratulatory, never accusatory
- always actionable
- conversion trigger appears exactly once, at the end
"""

from __future__ import annotations

from sentinel.pilot.audit_gap import AuditGapReport

PROGRESS_BAR_WIDTH = 14
PILOT_CONTACT_URL = "https://sentinel-kernel.eu/pilot"
PILOT_CONTACT_COPY = "30-minute call. No slides. No sales."


def render_audit_gap_text(report: AuditGapReport) -> str:
    """
    Render the full audit-gap report as human-readable text.

    Designed for a 64-column terminal but degrades gracefully on
    narrower ones. Uses ASCII glyphs only (no emojis).
    """
    lines: list[str] = []
    lines.append("")
    lines.append("Sentinel Audit Readiness — local pilot")
    lines.append("")
    lines.append(
        f"  Scope            {report.storage_path} "
        f"({report.trace_count} traces)"
    )
    lines.append(f"  Profile          {report.profile}")
    lines.append("")

    # Per-category rows
    for item in report.items:
        mark = _status_mark(item.status)
        lines.append(
            f"  {mark}  {item.label:<42}  {item.detail}"
        )
    lines.append("")

    # Score
    bar = _progress_bar(report.score, PROGRESS_BAR_WIDTH)
    lines.append(f"  Audit readiness  {bar}   {report.score} %")
    lines.append("")

    # Gap buckets
    library = list(report.library_gaps)
    deployment = list(report.deployment_gaps)
    organisational = list(report.organisational_gaps)

    lines.append(
        f"  Library gaps      (Sentinel can close these)         {len(library)}"
    )
    for gap in library:
        hint = gap.fix_hint or "see docs"
        lines.append(f"     > {hint}")
    if not library:
        lines.append("     (none)")

    lines.append("")
    lines.append(
        f"  Deployment gaps   (you must decide)                  {len(deployment)}"
    )
    for gap in deployment:
        lines.append(f"     . {gap.label.strip()}")
    if not deployment:
        lines.append("     (none)")

    lines.append("")
    lines.append(
        f"  Organisational    (human authorship required)        {len(organisational)}"
    )
    for gap in organisational:
        lines.append(f"     . {gap.label.strip()}")
    if not organisational:
        lines.append("     (none)")

    lines.append("")
    lines.append("  " + "-" * 58)
    lines.append(
        "  The library gets you to ~70 %. The last 30 % depends on"
    )
    lines.append(
        "  choices only your organisation can make: how long you"
    )
    lines.append(
        "  retain, who signs, where traces live, and what your"
    )
    lines.append(
        "  Annex IV document says."
    )
    lines.append("")
    lines.append(
        "  If you want to walk through this with someone who has"
    )
    lines.append(
        "  done it for a regulated EU buyer:"
    )
    lines.append(f"      {PILOT_CONTACT_URL}")
    lines.append(f"      {PILOT_CONTACT_COPY}")
    lines.append("")
    lines.append(
        "  Or close the gaps yourself — the library is sufficient."
    )
    lines.append("")

    return "\n".join(lines)


def render_quickstart_text(result: object) -> str:
    """
    Render the quickstart result as a short status block.

    Kept compact on purpose — users should see the next command
    without scrolling.
    """
    from sentinel.pilot.quickstart import QuickstartResult

    assert isinstance(result, QuickstartResult)

    lines: list[str] = []
    lines.append("")
    lines.append("Sentinel quickstart")
    lines.append("")

    if result.already_initialized:
        lines.append(f"  Already initialised at {result.pilot_dir}")
        lines.append(
            f"  Example file         {result.example_path} (unchanged)"
        )
        lines.append(
            f"  Config               {result.config_path} (unchanged)"
        )
        lines.append("")
        lines.append("  Re-run with --force to regenerate hello_sentinel.py.")
        lines.append("")
        lines.append("  Next    python hello_sentinel.py")
        lines.append("          sentinel audit-gap")
        lines.append("")
        return "\n".join(lines)

    created_example = (
        "created" if result.example_was_created
        else "overwritten" if result.example_was_overwritten
        else "unchanged"
    )
    created_config = "created" if result.config_was_created else "unchanged"

    lines.append(f"  Pilot dir            {result.pilot_dir}")
    lines.append(f"  Example file         {result.example_path}  ({created_example})")
    lines.append(f"  Config               {result.config_path}  ({created_config})")
    lines.append(f"  Storage              {result.db_path}")
    lines.append("")
    lines.append("  Next    python hello_sentinel.py")
    lines.append("          sentinel evidence-pack --output audit.pdf")
    lines.append("          sentinel audit-gap")
    lines.append("")
    return "\n".join(lines)


def render_fix_text(result: object) -> str:
    """Render a fix result as a compact two-block status update."""
    from sentinel.pilot.fixes import FixResult

    assert isinstance(result, FixResult)

    lines: list[str] = []
    lines.append("")
    lines.append(f"Sentinel fix: {result.fix_id}")
    lines.append("")
    lines.append(f"  {result.detail}")
    if result.artefact_path is not None:
        lines.append(f"  artefact      {result.artefact_path}")
    if result.config_path is not None:
        lines.append(f"  config        {result.config_path}")
    lines.append("")
    if result.points_delta > 0:
        lines.append(
            f"  audit-gap     +{result.points_delta} points  "
            f"(rerun: sentinel audit-gap)"
        )
    else:
        lines.append(
            "  audit-gap     no change  "
            "(already closed — run: sentinel audit-gap)"
        )
    lines.append("")
    return "\n".join(lines)


def render_status_text(status: object) -> str:
    """
    Render ``sentinel status`` as a compact activity + readiness block.

    Short enough to fit in a terminal without scrolling, shaped like
    the pilot-walkthrough — activity first (proof of use), then
    sovereignty and readiness, then a single audit-gap nudge when the
    readiness score is below a production-ready threshold.
    """
    from sentinel.pilot.status import PilotStatus

    assert isinstance(status, PilotStatus)

    act = status.activity
    readiness_bar = _progress_bar(status.audit_readiness, PROGRESS_BAR_WIDTH)
    sov_pct = int(round(status.sovereignty_score * 100))

    lines: list[str] = []
    lines.append("")
    lines.append("Sentinel status")
    lines.append("")
    lines.append(f"  Project           {status.project}")
    lines.append(f"  Version           {status.version}")
    lines.append(f"  Storage           {status.storage_kind}")
    lines.append("")
    lines.append(f"  Decision activity  (last {act.window_days} days)")
    if act.total == 0:
        lines.append(
            "     (no traces yet — run sentinel quickstart, "
            "then python hello_sentinel.py)"
        )
    else:
        lines.append(f"     Total           {act.total}")
        lines.append(f"     ALLOW           {act.allow}  ({act.allow_pct} %)")
        lines.append(f"     DENY            {act.deny}  ({act.deny_pct} %)")
        if act.exception:
            lines.append(f"     EXCEPTION       {act.exception}")
        if act.overrides:
            lines.append(f"     Override        {act.overrides}")
    lines.append("")
    lines.append(f"  Sovereignty score  {sov_pct} %")
    lines.append(
        f"  Audit readiness    {readiness_bar}   {status.audit_readiness} %"
    )
    lines.append("")

    if status.audit_readiness < 80:
        days = status.days_to_enforcement
        countdown = (
            f"{days} days to EU AI Act enforcement"
            if days >= 0
            else "EU AI Act is now enforced"
        )
        lines.append("  " + "-" * 58)
        lines.append(
            f"  {status.audit_readiness} % audit readiness — {countdown}."
        )
        lines.append("  Run: sentinel audit-gap")
        lines.append("  " + "-" * 58)
    else:
        lines.append(
            "  Production-ready score. Re-run `sentinel audit-gap` "
            "for the detailed split."
        )
    lines.append("")
    return "\n".join(lines)


def _status_mark(status: str) -> str:
    if status == "complete":
        return "+"
    if status == "partial":
        return "~"
    return "-"


def _progress_bar(score: int, width: int) -> str:
    """
    Render an ASCII progress bar for a 0..100 score.

    Uses block glyphs for visual weight but falls back gracefully in
    environments that cannot render them (they still take up the
    right number of columns).
    """
    score = max(0, min(100, score))
    filled = round((score / 100) * width)
    return "[" + ("#" * filled) + ("." * (width - filled)) + "]"
