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
    """
    Produce a single-file HTML sovereignty report.

    Usage::

        html = HTMLReport().generate(sentinel, manifesto=OurPolicy())
        Path("report.html").write_text(html)
    """

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
    now = datetime.now().isoformat(timespec="seconds")
    score = runtime.sovereignty_score

    score_cls = "score-green" if score >= 0.9 else ("score-amber" if score >= 0.6 else "score-red")

    compliance_rows = "".join(
        f"<tr><td>{e(a.article)}</td><td>{e(a.title)}</td>"
        f"<td class='status-{a.status.lower()}'>{e(a.status)}</td>"
        f"<td>{'auto' if a.automated else 'manual'}</td>"
        f"<td>{e(a.detail)}</td></tr>"
        for a in compliance.articles.values()
    )

    runtime_rows = "".join(
        f"<tr><td>{e(p.name)}</td><td>{e(p.version)}</td>"
        f"<td>{e(p.parent_company)}</td><td>{e(p.jurisdiction)}</td>"
        f"<td>{'yes' if p.cloud_act_exposure else 'no'}</td>"
        f"<td>{'yes' if p.in_critical_path else 'no'}</td></tr>"
        for p in runtime.packages[:50]  # cap display
    )

    cicd_rows = "".join(
        f"<tr><td>{e(f.file)}</td><td>{e(f.component)}</td>"
        f"<td>{e(f.vendor)}</td><td>{e(f.jurisdiction)}</td>"
        f"<td>{'yes' if f.cloud_act_exposure else 'no'}</td></tr>"
        for f in cicd.findings
    ) or "<tr><td colspan='5'>No CI/CD findings</td></tr>"

    infra_rows = "".join(
        f"<tr><td>{e(f.file)}</td><td>{e(f.component)}</td>"
        f"<td>{e(f.vendor)}</td><td>{e(f.jurisdiction)}</td>"
        f"<td>{'yes' if f.cloud_act_exposure else 'no'}</td></tr>"
        for f in infra.findings
    ) or "<tr><td colspan='5'>No infrastructure findings</td></tr>"

    manifesto_section = ""
    if manifesto_report is not None:
        dim_rows = "".join(
            f"<tr><td>{'✅' if d.satisfied else '❌'}</td>"
            f"<td>{e(d.name)}</td><td>{e(d.detail)}</td></tr>"
            for d in manifesto_report.sovereignty_dimensions.values()
        )
        manifesto_section = f"""
<h2>Manifesto status</h2>
<p>Overall score: <b>{manifesto_report.overall_score:.0%}</b></p>
<table><thead><tr><th></th><th>Dimension</th><th>Detail</th></tr></thead>
<tbody>{dim_rows}</tbody></table>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Sentinel Sovereignty Report — {e(sentinel.project)}</title>
<style>
 body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        max-width: 1100px; margin: 2em auto; padding: 0 1em; color: #111;
        background: #fff; }}
 h1 {{ font-size: 1.8em; margin-bottom: .2em; }}
 h2 {{ font-size: 1.3em; margin-top: 2.2em; border-bottom: 1px solid #ccc;
       padding-bottom: .3em; }}
 .meta {{ color: #555; font-size: .9em; }}
 .score {{ font-size: 3em; font-weight: 700; margin: .4em 0; }}
 .score-green {{ color: #167c3c; }}
 .score-amber {{ color: #a15c00; }}
 .score-red   {{ color: #a81717; }}
 table {{ border-collapse: collapse; width: 100%; margin-top: .6em; }}
 th, td {{ border: 1px solid #ddd; padding: .4em .6em; text-align: left;
          font-size: .92em; vertical-align: top; }}
 th {{ background: #f4f4f4; font-weight: 600; }}
 .status-compliant {{ background: #e6f4ea; color: #167c3c; }}
 .status-partial {{ background: #fff4e5; color: #a15c00; }}
 .status-non_compliant {{ background: #fce8e6; color: #a81717; }}
 .status-action_required {{ background: #f6f0ff; color: #53229c; }}
 .pill {{ display: inline-block; padding: .1em .5em; border-radius: .4em;
         font-size: .8em; background: #eee; }}
 footer {{ margin-top: 3em; padding-top: 1em; border-top: 1px solid #ccc;
          color: #888; font-size: .82em; }}
</style>
</head>
<body>

<h1>Sentinel Sovereignty Report</h1>
<p class="meta">
 Project: <b>{e(sentinel.project)}</b> ·
 Storage: <b>{e(sentinel.storage.backend_name)}</b> ·
 Data residency: <b>{e(sentinel.data_residency.value)}</b> ·
 Sovereign scope: <b>{e(sentinel.sovereign_scope)}</b>
</p>
<p class="meta">Generated: {now} · Days to EU AI Act enforcement: {compliance.days_to_enforcement}</p>

<div class="score {score_cls}">{score:.0%}</div>
<p>Runtime sovereignty score — fraction of installed packages with no CLOUD Act exposure.</p>

<h2>EU AI Act compliance</h2>
<p>Overall: <span class="pill">{e(compliance.overall)}</span> · Automated coverage: {compliance.automated_coverage:.0%}</p>
<table><thead><tr>
 <th>Article</th><th>Title</th><th>Status</th><th>Coverage</th><th>Detail</th>
</tr></thead><tbody>{compliance_rows}</tbody></table>

{manifesto_section}

<h2>Runtime packages ({runtime.total_packages} total, showing first 50)</h2>
<p>
 Sovereign: <b>{runtime.sovereign_packages}</b> ·
 US-owned: <b>{runtime.us_owned_packages}</b> ·
 Unknown: <b>{runtime.unknown_jurisdiction}</b>
</p>
<table><thead><tr>
 <th>Package</th><th>Version</th><th>Parent</th><th>Jurisdiction</th>
 <th>CLOUD Act</th><th>Critical path</th>
</tr></thead><tbody>{runtime_rows}</tbody></table>

<h2>CI/CD findings</h2>
<table><thead><tr>
 <th>File</th><th>Component</th><th>Vendor</th><th>Jurisdiction</th><th>CLOUD Act</th>
</tr></thead><tbody>{cicd_rows}</tbody></table>

<h2>Infrastructure findings</h2>
<table><thead><tr>
 <th>File</th><th>Component</th><th>Vendor</th><th>Jurisdiction</th><th>CLOUD Act</th>
</tr></thead><tbody>{infra_rows}</tbody></table>

<footer>
 Generated by sentinel-kernel. Apache 2.0. This report is fully
 self-contained; it loads no external resources and is safe to
 distribute in air-gapped environments.
</footer>
</body>
</html>
"""
