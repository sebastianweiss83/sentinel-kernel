"""
sentinel.dashboard.html
~~~~~~~~~~~~~~~~~~~~~~~
Self-contained HTML sovereignty report generator.

The output is a single HTML file with:
  - inline CSS (no external fonts, no CDN)
  - no external scripts
  - no <img src="http..."> or similar

Air-gapped safe by design: it must pass a grep for "http://" and "https://"
with zero hits on resource references.

Dark theme matching the GitHub Pages preview. Executive summary for
non-technical readers, SVG gauge, enforcement countdown, priority-
badged recommended actions, coloured dependency table, and a
"what to do" column in the EU AI Act table.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sentinel.compliance import EUAIActChecker
from sentinel.scanner import (
    CICDScanner,
    InfrastructureScanner,
    RuntimeScanner,
)

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.manifesto.base import SentinelManifesto


class HTMLReport:
    """Produce a single-file HTML sovereignty report."""

    def generate(
        self,
        sentinel: Sentinel,
        *,
        manifesto: SentinelManifesto | None = None,
        repo_root: str | Path = ".",
    ) -> str:
        runtime = RuntimeScanner().scan()
        cicd = CICDScanner().scan(repo_root)
        infra = InfrastructureScanner().scan(repo_root)
        compliance = EUAIActChecker().check(sentinel)

        manifesto_report = None
        if manifesto is not None:
            manifesto_report = manifesto.check(
                sentinel=sentinel,
                runtime_scan=runtime,
                cicd_scan=cicd,
                infra_scan=infra,
            )

        return _render_html(
            sentinel=sentinel,
            runtime=runtime,
            cicd=cicd,
            infra=infra,
            compliance=compliance,
            manifesto_report=manifesto_report,
        )


# ---------------------------------------------------------------------------
# CSS (design system matches docs/preview)
# ---------------------------------------------------------------------------

_CSS = r"""
:root {
  --bg: #0a0e14; --surface: #111827; --surface2: #1a2332;
  --border: #1f2937; --text: #e5e7eb; --text2: #9ca3af; --text3: #6b7280;
  --green: #00d084; --red: #ff3b3b; --amber: #f5a623; --blue: #3b82f6;
  --purple: #a78bfa;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.container { max-width: 1100px; margin: 0 auto; padding: 0 1.5rem; }
.mono { font-family: ui-monospace, "Cascadia Code", "Fira Code", Menlo, monospace; }
h1 { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 0.4rem; }
h2 {
  font-size: 1.5rem; font-weight: 700; margin-top: 3rem; margin-bottom: 1rem;
  padding-bottom: 0.5rem; border-bottom: 1px solid var(--border);
}
h3 { font-size: 1.05rem; font-weight: 700; margin-top: 1.6rem; margin-bottom: 0.6rem; color: var(--text); }
p { margin-bottom: 0.8rem; color: var(--text2); }
.meta { color: var(--text3); font-size: 0.9rem; margin-bottom: 0.3rem; }
.meta b { color: var(--text); font-weight: 600; }
a { color: var(--green); }

/* ---------- COUNTDOWN BAR ---------- */
.countdown {
  border-top: 3px solid var(--amber);
  border-bottom: 3px solid var(--amber);
  background: #2d1f00;
  padding: 1rem 0;
  margin: 1.5rem 0 2.5rem;
}
.countdown.urgent { background: #2d0b0b; border-color: var(--red); }
.countdown.safe { background: #0b2d1a; border-color: var(--green); }
.countdown-inner {
  display: flex; justify-content: space-between; align-items: center;
  gap: 2rem; flex-wrap: wrap;
}
.countdown-text { color: #ffd580; font-size: 0.98rem; max-width: 72ch; }
.countdown.urgent .countdown-text { color: #ffb3b3; }
.countdown.safe .countdown-text { color: #b3ffd9; }
.countdown-text strong { color: var(--amber); font-weight: 700; }
.countdown.urgent .countdown-text strong { color: var(--red); }
.countdown.safe .countdown-text strong { color: var(--green); }
.countdown-days {
  display: flex; flex-direction: column; align-items: center;
  padding: 0.5rem 1.2rem;
  background: rgba(245, 166, 35, 0.08);
  border: 1px solid var(--amber); border-radius: 8px;
}
.countdown.urgent .countdown-days { border-color: var(--red); background: rgba(255,59,59,0.08); }
.countdown.safe .countdown-days { border-color: var(--green); background: rgba(0,208,132,0.08); }
.countdown-days .n {
  font-size: 2rem; font-weight: 800; color: var(--amber); line-height: 1;
  font-family: ui-monospace, monospace;
}
.countdown.urgent .countdown-days .n { color: var(--red); }
.countdown.safe .countdown-days .n { color: var(--green); }
.countdown-days .label {
  font-size: 0.7rem; color: var(--text2); text-transform: uppercase;
  letter-spacing: 0.05em; margin-top: 0.2rem;
}

/* ---------- EXEC SUMMARY ---------- */
.exec {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 4px solid var(--green);
  border-radius: 8px;
  padding: 1.5rem 1.8rem;
  margin: 1.5rem 0 2.5rem;
}
.exec h3 {
  margin-top: 0;
  color: var(--green);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.8rem;
}
.exec p { color: var(--text); font-size: 1rem; margin-bottom: 0.6rem; }
.exec p:last-child { margin-bottom: 0; }

/* ---------- SCORE PANEL ---------- */
.score-grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 2rem;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.8rem;
  margin-bottom: 2rem;
}
.score-grid .gauge { display: flex; justify-content: center; }
.gauge-svg { display: block; }
.gauge-ring  { fill: none; stroke: #1f2937; stroke-width: 14; }
.gauge-fill  { fill: none; stroke-width: 14; stroke-linecap: round; transform: rotate(-90deg); transform-origin: 100px 100px; }
.gauge-fill.green { stroke: var(--green); }
.gauge-fill.amber { stroke: var(--amber); }
.gauge-fill.red { stroke: var(--red); }
.score-label { color: var(--text2); font-size: 0.85rem; margin-bottom: 0.3rem; text-transform: uppercase; letter-spacing: 0.08em; }
.score-explain { color: var(--text2); font-size: 0.92rem; }
.score-explain strong { color: var(--text); }

/* ---------- TABLES ---------- */
table {
  border-collapse: collapse; width: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  margin-top: 0.6rem;
  font-size: 0.9rem;
}
th, td {
  padding: 0.6rem 0.85rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
tbody tr:last-child td { border-bottom: none; }
th {
  background: var(--surface2);
  font-weight: 700;
  color: var(--text2);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
td { color: var(--text2); }
td.strong { color: var(--text); font-weight: 600; }
td.mono { font-family: ui-monospace, monospace; font-size: 0.85rem; }

/* EU-vs-US row accent */
tr.eu td:first-child { border-left: 3px solid var(--green); }
tr.us td:first-child { border-left: 3px solid var(--red); }
tr.unknown td:first-child { border-left: 3px solid var(--text3); }

/* ---------- STATUS BADGES ---------- */
.badge {
  display: inline-block;
  padding: 0.18rem 0.65rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.badge-compliant     { background: rgba(0, 208, 132, 0.15); color: var(--green); }
.badge-partial       { background: rgba(245, 166, 35, 0.15); color: var(--amber); }
.badge-non_compliant { background: rgba(255, 59, 59, 0.15); color: var(--red); }
.badge-action_required { background: rgba(167, 139, 250, 0.15); color: var(--purple); }
.badge-yes  { background: rgba(255, 59, 59, 0.15); color: var(--red); }
.badge-no   { background: rgba(0, 208, 132, 0.15); color: var(--green); }
.priority-critical { background: var(--red); color: #fff; }
.priority-high     { background: var(--amber); color: #1a0f00; }
.priority-medium   { background: var(--blue); color: #fff; }
.priority-low      { background: var(--text3); color: #fff; }

/* ---------- ACTIONS ---------- */
.actions { display: flex; flex-direction: column; gap: 0.8rem; margin-top: 1rem; }
.action {
  display: grid; grid-template-columns: 110px 1fr;
  gap: 1rem; align-items: start;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--amber);
  border-radius: 6px;
  padding: 0.9rem 1.1rem;
}
.action.critical { border-left-color: var(--red); }
.action.high     { border-left-color: var(--amber); }
.action.medium   { border-left-color: var(--blue); }
.action.low      { border-left-color: var(--text3); }
.action .title { color: var(--text); font-weight: 600; font-size: 0.95rem; margin-bottom: 0.2rem; }
.action .summary { color: var(--text); font-size: 0.9rem; margin-bottom: 0.35rem; }
.action .what { color: var(--text2); font-size: 0.85rem; margin-bottom: 0.5rem; }
.action .action-meta {
  font-size: 0.75rem;
  color: var(--text3);
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
  border-top: 1px dashed var(--border);
  padding-top: 0.5rem;
  margin-top: 0.2rem;
}
.action .action-meta-label {
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text3);
}
.action .action-meta-value { color: var(--text2); font-weight: 600; }
.action .action-meta-sep { color: var(--border); }

/* ---------- NEXT STEPS ---------- */
.next-steps {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 4px solid var(--blue);
  border-radius: 8px;
  padding: 1.4rem 1.8rem;
  margin-top: 1rem;
}
.next-steps ol {
  margin: 0.8rem 0 0 1.4rem;
  padding: 0;
  color: var(--text2);
}
.next-steps li {
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
}
.next-steps li strong { color: var(--text); }
.next-steps code {
  font-family: ui-monospace, monospace;
  background: #0a0e14;
  padding: 0.12rem 0.45rem;
  border-radius: 3px;
  color: var(--green);
  font-size: 0.85rem;
  border: 1px solid var(--border);
}

/* ---------- MANIFESTO ---------- */
.manifesto-score {
  font-size: 2rem; font-weight: 800; color: var(--green);
  font-family: ui-monospace, monospace;
}

/* ---------- FOOTER ---------- */
footer {
  margin-top: 3.5rem;
  padding: 1.5rem 0 2.5rem;
  border-top: 1px solid var(--border);
  color: var(--text3);
  font-size: 0.82rem;
}

@media (max-width: 780px) {
  .score-grid { grid-template-columns: 1fr; }
  .countdown-inner { flex-direction: column; align-items: flex-start; }
  .action { grid-template-columns: 1fr; }
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gauge_svg(score: float) -> str:
    """Render a circular sovereignty score gauge (inline SVG)."""
    s = max(0.0, min(1.0, score))
    colour_cls = "green" if s >= 0.9 else ("amber" if s >= 0.6 else "red")
    r = 70
    circumference = 2 * 3.1415926 * r  # ≈ 440
    offset = circumference * (1 - s)
    return f"""
<svg class="gauge-svg" viewBox="0 0 200 200" width="200" height="200" xmlns="http://www.w3.org/2000/svg">
  <circle class="gauge-ring" cx="100" cy="100" r="{r}"/>
  <circle class="gauge-fill {colour_cls}" cx="100" cy="100" r="{r}"
          stroke-dasharray="{circumference:.2f}"
          stroke-dashoffset="{offset:.2f}"/>
  <text x="100" y="112" text-anchor="middle"
        font-family="ui-monospace, monospace" font-size="36" font-weight="800"
        fill="#e5e7eb">{s:.0%}</text>
</svg>
""".strip()


def _countdown_classes(days: int) -> str:
    if days < 0:
        return "countdown safe"
    if days < 90:
        return "countdown urgent"
    return "countdown"


_ACTION_GUIDANCE: dict[str, dict[str, str]] = {
    "Art. 9": {
        "summary": "Implement a formal risk management process.",
        "detail": (
            "Document risk categories for each AI use case, assign risk "
            "owners, and wire a PolicyEvaluator (SimpleRuleEvaluator or "
            "LocalRegoEvaluator) into Sentinel so every decision is "
            "checked against the documented risks."
        ),
        "deadline": "Before deployment",
        "owner": "Engineering + Risk",
    },
    "Art. 12": {
        "summary": "Enable tamper-resistant trace persistence.",
        "detail": (
            "Configure a StorageBackend (SQLite, PostgreSQL, or "
            "Filesystem) so every @sentinel.trace call is stored "
            "append-only. Verify with sentinel verify --all."
        ),
        "deadline": "Before deployment",
        "owner": "Engineering",
    },
    "Art. 13": {
        "summary": "Populate transparency metadata on every trace.",
        "detail": (
            "Ensure agent, model, model_version, and policy fields are "
            "set on every DecisionTrace. Run sentinel compliance check "
            "to confirm Art. 13 shows as COMPLIANT."
        ),
        "deadline": "Before deployment",
        "owner": "Engineering",
    },
    "Art. 14": {
        "summary": "Prove the kill switch works end-to-end.",
        "detail": (
            "Test engage_kill_switch() in a staging environment. "
            "Confirm blocked calls raise KillSwitchEngaged and produce "
            "DENY traces with a HumanOverride entry."
        ),
        "deadline": "Before deployment",
        "owner": "Engineering + Ops",
    },
    "Art. 17": {
        "summary": "Establish a quality management system for AI outputs.",
        "detail": (
            "Define accuracy thresholds and monitoring intervals. Wire "
            "sentinel compliance check into CI on every release so "
            "quality metrics are versioned alongside the code."
        ),
        "deadline": "Before deployment",
        "owner": "Quality + Engineering",
    },
    "Art. 10": {
        "summary": "Document training data governance end-to-end.",
        "detail": (
            "Record training data sources, quality controls, bias "
            "assessments, and data governance policies. This is a "
            "human process — Sentinel cannot automate it. See "
            "docs/bsi-profile.md for the BSI-aligned template."
        ),
        "deadline": "Your team must implement",
        "owner": "Data + Legal",
    },
    "Art. 15": {
        "summary": "Define accuracy metrics for your specific use case.",
        "detail": (
            "Choose accuracy, robustness, and cybersecurity metrics "
            "that match the domain risk. Implement monitoring and "
            "drift alerting. This is a human process — Sentinel "
            "cannot automate the metric choice."
        ),
        "deadline": "Your team must implement",
        "owner": "Data + Engineering",
    },
    "Art. 16": {
        "summary": "Complete provider registration, conformity assessment, CE marking.",
        "detail": (
            "Art. 16(d) deployer logging and 16(f) post-market monitoring evidence are "
            "produced automatically via the trace store. Register your AI system in the "
            "EU AI Act database (Art. 71). Conduct conformity assessment (Annex VI or VII "
            "depending on risk class). Affix CE marking. Registration and conformity "
            "assessment are human deliverables."
        ),
        "deadline": "Before market placement",
        "owner": "Legal + Compliance",
    },
    "Art. 26": {
        "summary": "Document human oversight procedures and train staff.",
        "detail": (
            "Art. 26(5) deployer logging and Art. 26(6) human oversight primitives "
            "(kill switch + trace store) are shipped by Sentinel. Document human oversight "
            "procedures in writing. Define escalation paths when kill switch is engaged. "
            "Train operational staff on AI system limitations and override process. "
            "Establish incident reporting workflow."
        ),
        "deadline": "Before deployment",
        "owner": "Operations + Legal",
    },
    "Art. 72": {
        "summary": "Publish a GPAI post-market monitoring plan (if applicable).",
        "detail": (
            "Records model identity, inputs hash, outputs and decision chain for any "
            "GPAI call — the raw evidence Art. 72 requires. Only applies if deploying a "
            "GPAI model as high-risk system. Publish a GPAI post-market monitoring plan. "
            "Maintain model cards and capability evaluations. Sentinel provides the audit "
            "trail automatically."
        ),
        "deadline": "Before deployment (only if GPAI applies)",
        "owner": "Engineering + Legal",
    },
}


def _action_for(article: str) -> dict[str, str]:
    return _ACTION_GUIDANCE.get(
        article,
        {
            "summary": "Review manually.",
            "detail": "No automated guidance available for this article.",
            "deadline": "—",
            "owner": "Team",
        },
    )


_CLOUD_ACT_YES = '<span class="badge badge-yes">YES</span>'
_CLOUD_ACT_NO = '<span class="badge badge-no">NO</span>'


def _cloud_act_badge(flag: bool) -> str:
    return _CLOUD_ACT_YES if flag else _CLOUD_ACT_NO


def _status_priority(status: str) -> tuple[str, str]:
    """Return (priority_class, priority_label)."""
    status = (status or "").upper()
    if status == "NON_COMPLIANT":
        return "critical", "CRITICAL"
    if status == "PARTIAL":
        return "high", "HIGH"
    if status == "ACTION_REQUIRED":
        return "medium", "MEDIUM"
    return "low", "LOW"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_html(
    *,
    sentinel: Sentinel,
    runtime: Any,
    cicd: Any,
    infra: Any,
    compliance: Any,
    manifesto_report: Any,
) -> str:
    e = html.escape
    # ``SENTINEL_REPORT_TIMESTAMP`` overrides the generated-at stamp so
    # that tooling (scripts/sync_all.py, CI) can produce byte-identical
    # output on repeated runs. Without it, the current wall clock is used.
    import os as _os
    now = _os.environ.get(
        "SENTINEL_REPORT_TIMESTAMP",
        datetime.now().isoformat(timespec="seconds"),
    )
    score = runtime.sovereignty_score
    days = compliance.days_to_enforcement
    countdown_cls = _countdown_classes(days)
    gauge = _gauge_svg(score)

    # Executive summary — plain English
    if score >= 0.9:
        summary_headline = "Your system meets EU sovereignty requirements."
    elif score >= 0.6:
        summary_headline = "Your system is partially sovereign. Action required."
    else:
        summary_headline = "Your system has significant sovereignty gaps."

    overall = getattr(compliance, "overall", "UNKNOWN")
    auto_coverage = getattr(compliance, "automated_coverage", 0.0)

    # Compliance table with "what to do" column
    compliance_rows = []
    # Each action_item: (priority_cls, priority_label, title, summary, detail, deadline, owner)
    action_items: list[tuple[str, str, str, str, str, str, str]] = []
    for a in compliance.articles.values():
        status_cls = f"badge-{a.status.lower()}"
        guidance = _action_for(a.article)
        what_to_do_cell = (
            f"<div class='strong' style='color:var(--text);margin-bottom:0.2rem;'>{e(guidance['summary'])}</div>"
            f"<div style='font-size:0.82rem;color:var(--text3);'>"
            f"{e(guidance['deadline'])} · {e(guidance['owner'])}"
            f"</div>"
        )
        compliance_rows.append(
            f"<tr>"
            f"<td class='strong mono'>{e(a.article)}</td>"
            f"<td>{e(a.title)}</td>"
            f"<td><span class='badge {status_cls}'>{e(a.status)}</span></td>"
            f"<td>{e(a.detail)}</td>"
            f"<td>{what_to_do_cell}</td>"
            f"</tr>"
        )
        if a.status.upper() in {"NON_COMPLIANT", "PARTIAL", "ACTION_REQUIRED"}:
            pcls, plabel = _status_priority(a.status)
            action_items.append(
                (
                    pcls,
                    plabel,
                    f"{a.article} — {a.title}",
                    guidance["summary"],
                    guidance["detail"],
                    guidance["deadline"],
                    guidance["owner"],
                )
            )
    compliance_tbody = "".join(compliance_rows)

    # Runtime package table — coloured by jurisdiction
    runtime_rows = []
    for p in runtime.packages[:60]:
        if p.cloud_act_exposure:
            row_cls = "us"
            cloud_badge = _CLOUD_ACT_YES
        elif p.jurisdiction.upper() in {"UNKNOWN", ""}:
            row_cls = "unknown"
            cloud_badge = "<span class=\"badge badge-no\">—</span>"
        else:
            row_cls = "eu"
            cloud_badge = _CLOUD_ACT_NO
        runtime_rows.append(
            f"<tr class='{row_cls}'>"
            f"<td class='strong mono'>{e(p.name)}</td>"
            f"<td class='mono'>{e(p.version)}</td>"
            f"<td>{e(p.parent_company)}</td>"
            f"<td>{e(p.jurisdiction)}</td>"
            f"<td>{cloud_badge}</td>"
            f"<td>{'yes' if p.in_critical_path else 'no'}</td>"
            f"</tr>"
        )
    runtime_tbody = "".join(runtime_rows)

    cicd_rows = "".join(
        f"<tr class='{'us' if f.cloud_act_exposure else 'eu'}'>"
        f"<td class='mono'>{e(f.file)}</td>"
        f"<td>{e(f.component)}</td>"
        f"<td>{e(f.vendor)}</td>"
        f"<td>{e(f.jurisdiction)}</td>"
        f"<td>{_cloud_act_badge(f.cloud_act_exposure)}</td>"
        f"</tr>"
        for f in cicd.findings
    ) or "<tr><td colspan='5' style='text-align:center;color:var(--text3);'>No CI/CD findings</td></tr>"

    infra_rows = "".join(
        f"<tr class='{'us' if f.cloud_act_exposure else 'eu'}'>"
        f"<td class='mono'>{e(f.file)}</td>"
        f"<td>{e(f.component)}</td>"
        f"<td>{e(f.vendor)}</td>"
        f"<td>{e(f.jurisdiction)}</td>"
        f"<td>{_cloud_act_badge(f.cloud_act_exposure)}</td>"
        f"</tr>"
        for f in infra.findings
    ) or "<tr><td colspan='5' style='text-align:center;color:var(--text3);'>No infrastructure findings</td></tr>"

    manifesto_section = ""
    if manifesto_report is not None:
        dim_rows = "".join(
            f"<tr>"
            f"<td class='strong'>{'✓' if d.satisfied else '✗'}</td>"
            f"<td class='strong'>{e(d.name)}</td>"
            f"<td>{e(d.detail)}</td>"
            f"</tr>"
            for d in manifesto_report.sovereignty_dimensions.values()
        )
        manifesto_section = f"""
<h2>Manifesto status</h2>
<p>Overall manifesto score: <span class="manifesto-score">{manifesto_report.overall_score:.0%}</span></p>
<table>
  <thead><tr><th style='width:60px;'></th><th>Dimension</th><th>Detail</th></tr></thead>
  <tbody>{dim_rows}</tbody>
</table>
"""

    # Recommended actions block (priority badges + structured remediation)
    if action_items:
        action_items.sort(
            key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x[0]]
        )
        actions_html = "\n".join(
            f"""
<div class="action {cls}">
  <span class="badge priority-{cls}">{plabel}</span>
  <div>
    <div class="title">{e(title)}</div>
    <div class="summary">{e(summary)}</div>
    <div class="what">{e(detail)}</div>
    <div class="action-meta">
      <span class="action-meta-label">Deadline</span>
      <span class="action-meta-value">{e(deadline)}</span>
      <span class="action-meta-sep">·</span>
      <span class="action-meta-label">Owner</span>
      <span class="action-meta-value">{e(owner)}</span>
    </div>
  </div>
</div>
"""
            for cls, plabel, title, summary, detail, deadline, owner in action_items
        )
    else:
        actions_html = (
            "<p style='color:var(--green);'>✓ No outstanding actions. "
            "All EU AI Act articles are either compliant or marked for human action.</p>"
        )

    # Countdown banner text (urgency-aware)
    if days < 0:
        countdown_text = "<strong>EU AI Act Annex III is now in force.</strong> High-risk AI systems must prove automatic tamper-resistant logging. Penalties up to €15M or 3% of global turnover."
    elif days < 90:
        countdown_text = "<strong>Less than 90 days to enforcement.</strong> EU AI Act Annex III — 2 August 2026. Automatic tamper-resistant logging is mandatory for high-risk systems."
    else:
        countdown_text = "<strong>EU AI Act Annex III enforcement: 2 August 2026.</strong> High-risk AI systems must prove automatic tamper-resistant logging."

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Sovereignty Report — {e(sentinel.project)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">

<h1>Sentinel Sovereignty Report</h1>
<div class="meta">Project: <b>{e(sentinel.project)}</b> · Storage: <b>{e(sentinel.storage.backend_name)}</b> · Data residency: <b>{e(sentinel.data_residency.value)}</b> · Sovereign scope: <b>{e(sentinel.sovereign_scope)}</b></div>
<div class="meta">Generated: {now}</div>

<div class="{countdown_cls}">
  <div class="countdown-inner" style="max-width:1100px;margin:0 auto;padding:0 1.5rem;">
    <div class="countdown-text">{countdown_text}</div>
    <div class="countdown-days">
      <div class="n">{max(0, days)}</div>
      <div class="label">days remaining</div>
    </div>
  </div>
</div>

<div class="exec">
  <h3>Executive summary</h3>
  <p><strong>{e(summary_headline)}</strong></p>
  <p>The runtime sovereignty score is <strong>{score:.0%}</strong> — that is the fraction of installed Python packages with no US CLOUD Act exposure. EU AI Act overall status: <strong>{e(overall)}</strong>. Automated coverage of the required articles: <strong>{auto_coverage:.0%}</strong>.</p>
  <p>Where the report flags partial or non-compliant items, the "recommended actions" block below names each one in priority order. Every action corresponds to a specific file or configuration change.</p>
</div>

<div class="score-grid">
  <div class="gauge">{gauge}</div>
  <div>
    <div class="score-label">Sovereignty score</div>
    <p class="score-explain">
      <strong>{runtime.sovereign_packages}</strong> of <strong>{runtime.total_packages}</strong> installed packages are EU-sovereign or neutral.
      <strong>{runtime.us_owned_packages}</strong> are US-incorporated and subject to the CLOUD Act. <strong>{runtime.unknown_jurisdiction}</strong> are unknown.
    </p>
    <p class="score-explain">
      Critical-path violations: <strong>{len(runtime.critical_path_violations)}</strong>.
      This is a runtime snapshot. CI/CD and infrastructure are reported separately below.
    </p>
  </div>
</div>

<h2>EU AI Act compliance</h2>
<p>Overall: <span class="badge badge-{overall.lower()}">{e(overall)}</span>  ·  Automated coverage: <strong style="color:var(--text);">{auto_coverage:.0%}</strong></p>
<table>
  <thead>
    <tr>
      <th style="width:80px;">Article</th>
      <th>Title</th>
      <th style="width:150px;">Status</th>
      <th>Detail</th>
      <th>What to do</th>
    </tr>
  </thead>
  <tbody>{compliance_tbody}</tbody>
</table>

<h2>Recommended actions</h2>
<div class="actions">
{actions_html}
</div>

<h2>Next steps</h2>
<div class="next-steps">
  <p>Once the actions above are resolved, proceed in this order:</p>
  <ol>
    <li><strong>Generate an attestation</strong> you can share with auditors:<br>
        <code>sentinel attestation generate --output governance.json</code></li>
    <li><strong>Run the manifesto + compliance check</strong> and attach the output to your change request:<br>
        <code>sentinel compliance check --all-frameworks</code></li>
    <li><strong>Schedule BSI pre-engagement</strong> — the pre-engagement package is already in
        <code>docs/bsi-pre-engagement/</code>. Contact:
        <strong style="color:var(--text);">ki-sicherheit@bsi.bund.de</strong>
        (bsi.bund.de/KI)</li>
    <li><strong>EU AI Act Annex III enforcement: {max(0, days)} days</strong> remaining
        (2 August 2026). Penalties up to €15M or 3% of global annual turnover.</li>
  </ol>
</div>

{manifesto_section}

<h2>Runtime packages</h2>
<p>Showing first 60 of <strong style="color:var(--text);">{runtime.total_packages}</strong> installed packages. Sovereign: <strong style="color:var(--green);">{runtime.sovereign_packages}</strong> · US-owned: <strong style="color:var(--red);">{runtime.us_owned_packages}</strong> · Unknown: <strong style="color:var(--text3);">{runtime.unknown_jurisdiction}</strong></p>
<p style="font-size:0.85rem;color:var(--text3);">Showing packages in the current Python environment. For a complete scan including your project dependencies, run <code style="font-family:ui-monospace,monospace;background:#0a0e14;padding:0.12rem 0.45rem;border-radius:3px;color:var(--green);font-size:0.85rem;border:1px solid var(--border);">sentinel report</code> from your project directory with your virtual environment activated.</p>
<table>
  <thead>
    <tr>
      <th>Package</th>
      <th>Version</th>
      <th>Parent</th>
      <th>Jurisdiction</th>
      <th>CLOUD Act</th>
      <th>Critical</th>
    </tr>
  </thead>
  <tbody>{runtime_tbody}</tbody>
</table>

<h2>CI/CD findings</h2>
<table>
  <thead>
    <tr>
      <th>File</th>
      <th>Component</th>
      <th>Vendor</th>
      <th>Jurisdiction</th>
      <th>CLOUD Act</th>
    </tr>
  </thead>
  <tbody>{cicd_rows}</tbody>
</table>

<h2>Infrastructure findings</h2>
<table>
  <thead>
    <tr>
      <th>File</th>
      <th>Component</th>
      <th>Vendor</th>
      <th>Jurisdiction</th>
      <th>CLOUD Act</th>
    </tr>
  </thead>
  <tbody>{infra_rows}</tbody>
</table>

<footer>
  Generated by <b style="color:var(--text2);">sentinel-kernel</b>. Apache 2.0. This report is fully
  self-contained — it loads no external resources and is safe to distribute in
  air-gapped environments.
</footer>

</div>
</body>
</html>
"""
