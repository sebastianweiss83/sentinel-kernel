"""
sentinel.compliance.evidence_pack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Quarterly / ad-hoc evidence pack PDF for auditors.

Wraps existing Sentinel evidence generators (EUAIActChecker,
DoraChecker, NIS2Checker, generate_attestation, RuntimeScanner)
into a single self-contained PDF suitable for an audit binder or
BSI pre-engagement submission.

All content comes from existing public APIs. This module only
handles rendering. It adds no new business logic, no new crypto,
no new runtime behaviour.

Optional dependency: install ``sentinel-kernel[pdf]`` which pulls
in ``reportlab`` (BSD-3-Clause, UK-based, pure Python). Without
the extra, importing this module still succeeds but
``render_evidence_pdf`` raises ``ImportError`` with a helpful
message.

Air-gapped: reportlab ships its own fonts. No network calls.
"""

from __future__ import annotations

import hashlib
import html
import json as _json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sentinel.compliance.dora import DoraChecker
from sentinel.compliance.euaiact import EUAIActChecker
from sentinel.compliance.nis2 import NIS2Checker
from sentinel.core.attestation import generate_attestation
from sentinel.core.trace import PolicyResult
from sentinel.scanner.runtime import RuntimeScanner

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace
    from sentinel.core.tracer import Sentinel
    from sentinel.manifesto.base import SentinelManifesto


_MISSING_DEP_MESSAGE = (
    "Sentinel evidence-pack requires reportlab. Install the extra:\n"
    "    pip install sentinel-kernel[pdf]"
)

#: Storage pagination size for trace window iteration. Overridable
#: by tests to exercise the multi-page branch without seeding 500+
#: traces.
_PAGE_SIZE = 500


def _import_reportlab() -> Any:
    try:
        import reportlab  # noqa: F401
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return reportlab


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------


@dataclass
class EvidencePackOptions:
    """Window and scope controls for an evidence pack."""

    since: datetime | None = None
    until: datetime | None = None
    project: str | None = None
    financial_sector: bool = False
    critical_infrastructure: bool = False
    max_traces: int = 10_000
    title: str = "Sentinel Evidence Pack"


@dataclass
class ExecutiveSummary:
    """Aggregated trace statistics for the pack window."""

    trace_count: int
    allow_count: int
    deny_count: int
    exception_count: int
    override_count: int
    unique_agents: int
    unique_policies: int
    truncated: bool = False


# ---------------------------------------------------------------------------
# Pure helpers (no reportlab required)
# ---------------------------------------------------------------------------


def _iter_traces_in_window(
    sentinel: Sentinel, options: EvidencePackOptions
) -> Iterator[DecisionTrace]:
    """Paginate over stored traces, yielding those within the window.

    Mirrors the pagination pattern in
    ``sentinel.storage.base.export_ndjson`` so there is no coupling
    to any specific storage backend.
    """
    page_size = _PAGE_SIZE
    offset = 0
    yielded = 0
    while True:
        page = sentinel.storage.query(
            project=options.project,
            limit=page_size,
            offset=offset,
        )
        if not page:
            return
        for trace in page:
            if (
                options.since
                and trace.started_at
                and trace.started_at < options.since
            ):
                continue
            if (
                options.until
                and trace.started_at
                and trace.started_at >= options.until
            ):
                continue
            yield trace
            yielded += 1
            if yielded >= options.max_traces:
                return
        if len(page) < page_size:
            return
        offset += page_size


def _build_executive_summary(
    traces: list[DecisionTrace], *, truncated: bool
) -> ExecutiveSummary:
    allow = deny = exception = override = 0
    agents: set[str] = set()
    policies: set[str] = set()
    for t in traces:
        agents.add(t.agent)
        pe = t.policy_evaluation
        if pe is not None:
            if pe.result == PolicyResult.ALLOW:
                allow += 1
            elif pe.result == PolicyResult.DENY:
                deny += 1
            elif pe.result == PolicyResult.EXCEPTION:
                exception += 1
            if pe.policy_id:
                policies.add(pe.policy_id)
        if t.human_override is not None:
            override += 1
    return ExecutiveSummary(
        trace_count=len(traces),
        allow_count=allow,
        deny_count=deny,
        exception_count=exception,
        override_count=override,
        unique_agents=len(agents),
        unique_policies=len(policies),
        truncated=truncated,
    )


def _hash_manifest_digest(hash_lines: list[str]) -> str:
    """SHA-256 of the concatenated hash lines. Deterministic."""
    joined = "\n".join(hash_lines)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _esc(s: Any) -> str:
    """HTML-escape for reportlab Paragraph content."""
    return html.escape(str(s))


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------


def render_evidence_pdf(
    sentinel: Sentinel,
    options: EvidencePackOptions,
    output: str | Path,
    *,
    manifesto: SentinelManifesto | None = None,
) -> Path:
    """
    Render a self-contained evidence pack PDF.

    :param sentinel: a configured :class:`Sentinel` instance.
    :param options: window + scope controls.
    :param output: path to write the PDF.
    :param manifesto: optional :class:`SentinelManifesto` — included
        in the sovereign attestation appendix.
    :raises ImportError: if reportlab is not installed.
    :returns: the path the PDF was written to.
    """
    _import_reportlab()

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    h1 = styles["Heading1"]
    mono = styles["Code"]

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=options.title,
        author=f"sentinel-kernel {sentinel.project}",
    )

    flow: list[Any] = []

    grid_style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ]
    )

    # --- Cover page --------------------------------------------------------
    flow.append(Paragraph(_esc(options.title), h1))
    flow.append(Spacer(1, 6 * mm))
    cover_meta = [
        ["Project", _esc(sentinel.project)],
        ["Sovereign scope", _esc(sentinel.sovereign_scope)],
        ["Data residency", _esc(sentinel.data_residency.value)],
        ["Storage backend", _esc(sentinel.storage.backend_name)],
        [
            "Generated (UTC)",
            _esc(datetime.now(UTC).isoformat(timespec="seconds")),
        ],
        [
            "Since",
            _esc(options.since.isoformat() if options.since else "—"),
        ],
        [
            "Until",
            _esc(options.until.isoformat() if options.until else "—"),
        ],
    ]
    cover_table = Table(cover_meta, colWidths=[50 * mm, 110 * mm])
    cover_table.setStyle(grid_style)
    flow.append(cover_table)
    flow.append(Spacer(1, 8 * mm))
    flow.append(
        Paragraph(
            "This evidence pack is produced by the Sentinel decision "
            "trace and policy enforcement layer. It documents "
            "Art. 12 / 13 / 14 / 17 technical controls. It does "
            "<b>not</b> replace risk management, data governance, "
            "conformity assessment, or post-market monitoring.",
            body,
        )
    )
    flow.append(PageBreak())

    # --- Collect traces once (used by several sections) -------------------
    traces = list(_iter_traces_in_window(sentinel, options))
    truncated = len(traces) >= options.max_traces
    summary = _build_executive_summary(traces, truncated=truncated)

    # --- Executive summary ------------------------------------------------
    flow.append(Paragraph("Executive summary", h1))
    flow.append(Spacer(1, 4 * mm))
    summary_rows = [
        ["Traces in window", str(summary.trace_count)],
        ["ALLOW", str(summary.allow_count)],
        ["DENY", str(summary.deny_count)],
        ["EXCEPTION_REQUIRED", str(summary.exception_count)],
        ["Human overrides", str(summary.override_count)],
        ["Unique agents", str(summary.unique_agents)],
        ["Unique policies", str(summary.unique_policies)],
        ["Truncated", "yes" if summary.truncated else "no"],
    ]
    summary_table = Table(summary_rows, colWidths=[70 * mm, 90 * mm])
    summary_table.setStyle(grid_style)
    flow.append(summary_table)
    flow.append(PageBreak())

    # --- EU AI Act section -------------------------------------------------
    eu_report = EUAIActChecker().check(sentinel)
    flow.append(Paragraph("EU AI Act coverage", h1))
    flow.append(Spacer(1, 2 * mm))
    for line in eu_report.as_text().splitlines():
        flow.append(Paragraph(_esc(line) or "&nbsp;", mono))
    flow.append(PageBreak())

    # --- DORA section (optional) -------------------------------------------
    if options.financial_sector:
        dora_report = DoraChecker().check(sentinel)
        flow.append(Paragraph("DORA coverage", h1))
        flow.append(Spacer(1, 2 * mm))
        for line in dora_report.as_text().splitlines():
            flow.append(Paragraph(_esc(line) or "&nbsp;", mono))
        flow.append(PageBreak())

    # --- NIS2 section (optional) -------------------------------------------
    if options.critical_infrastructure:
        nis2_report = NIS2Checker().check(sentinel)
        flow.append(Paragraph("NIS2 coverage", h1))
        flow.append(Spacer(1, 2 * mm))
        for line in nis2_report.as_text().splitlines():
            flow.append(Paragraph(_esc(line) or "&nbsp;", mono))
        flow.append(PageBreak())

    # --- Trace samples -----------------------------------------------------
    flow.append(Paragraph("Trace samples", h1))
    flow.append(Spacer(1, 2 * mm))
    if not traces:
        flow.append(
            Paragraph("No traces in the selected window.", body)
        )
    else:
        sample_rows: list[list[str]] = [
            ["trace_id", "agent", "result", "started_at"]
        ]
        head = traces[:10]
        tail = traces[-10:] if len(traces) > 10 else []
        seen: set[str] = set()
        picked: list[DecisionTrace] = []
        for t in head + tail:
            if t.trace_id in seen:
                continue
            seen.add(t.trace_id)
            picked.append(t)
        for t in picked:
            result = "—"
            if t.policy_evaluation is not None:
                result = t.policy_evaluation.result.value
            sample_rows.append(
                [
                    t.trace_id[:12] + "…",
                    _esc(t.agent),
                    _esc(result),
                    _esc(
                        t.started_at.isoformat(timespec="seconds")
                        if t.started_at
                        else "—"
                    ),
                ]
            )
        sample_table = Table(
            sample_rows,
            colWidths=[40 * mm, 50 * mm, 30 * mm, 50 * mm],
        )
        sample_table.setStyle(grid_style)
        flow.append(sample_table)
    flow.append(PageBreak())

    # --- Hash manifest -----------------------------------------------------
    flow.append(Paragraph("Hash manifest", h1))
    flow.append(Spacer(1, 2 * mm))
    hash_lines = [
        f"{t.trace_id} inputs={t.inputs_hash or '-'} "
        f"output={t.output_hash or '-'}"
        for t in traces
    ]
    pack_digest = _hash_manifest_digest(hash_lines)
    flow.append(
        Paragraph(
            "The evidence pack digest is a SHA-256 of the trace hash "
            "list. Recompute it from the NDJSON export of the same "
            "window to verify this pack covers the same traces.",
            body,
        )
    )
    flow.append(Spacer(1, 2 * mm))
    flow.append(Paragraph(f"<b>Pack digest:</b> {pack_digest}", mono))
    flow.append(Spacer(1, 3 * mm))
    if hash_lines:
        display_rows = hash_lines[:200]
        for line in display_rows:
            flow.append(Paragraph(_esc(line), mono))
        if len(hash_lines) > len(display_rows):
            flow.append(
                Paragraph(
                    f"… {len(hash_lines) - len(display_rows)} more "
                    "entries truncated (full list in NDJSON export).",
                    body,
                )
            )
    else:
        flow.append(
            Paragraph("No hash entries — empty trace window.", body)
        )
    flow.append(PageBreak())

    # --- Attestation appendix ---------------------------------------------
    attestation = generate_attestation(
        sentinel=sentinel,
        manifesto=manifesto,
        compliance_report=eu_report,
    )
    flow.append(Paragraph("Sovereign attestation", h1))
    flow.append(Spacer(1, 2 * mm))
    flow.append(
        Paragraph(
            "Self-contained governance attestation. The attestation "
            "hash is a SHA-256 of the document content (sorted keys). "
            "Verifiable offline with <i>sentinel attestation verify</i>.",
            body,
        )
    )
    flow.append(Spacer(1, 3 * mm))
    attestation_json = _json.dumps(
        attestation, indent=2, sort_keys=True, default=str
    )
    for line in attestation_json.splitlines():
        flow.append(Paragraph(_esc(line) or "&nbsp;", mono))
    flow.append(PageBreak())

    # --- Sovereignty scan appendix ----------------------------------------
    scan = RuntimeScanner().scan()
    flow.append(Paragraph("Dependency sovereignty scan", h1))
    flow.append(Spacer(1, 2 * mm))
    flow.append(
        Paragraph(
            f"Packages scanned: {scan.total_packages}. Sovereign: "
            f"{scan.sovereign_packages}. US-owned: "
            f"{scan.us_owned_packages}. Unknown: "
            f"{scan.unknown_jurisdiction}. Sovereignty score: "
            f"{scan.sovereignty_score:.0%}. Critical-path "
            f"violations: {len(scan.critical_path_violations)}.",
            body,
        )
    )
    if scan.critical_path_violations:
        flow.append(Spacer(1, 2 * mm))
        for violation in scan.critical_path_violations:
            flow.append(
                Paragraph(f"VIOLATION: {_esc(violation)}", mono)
            )

    doc.build(flow)
    return output_path
