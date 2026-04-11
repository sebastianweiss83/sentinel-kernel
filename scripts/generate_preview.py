#!/usr/bin/env python3
"""
Generate the static GitHub Pages preview.

Produces:
  docs/preview/index.html   — landing page with live sample dashboard
  docs/preview/report.html  — full self-contained sovereignty report

Both files are fully self-contained: no external CDNs, no external
fonts, no external scripts. Safe to serve as GitHub Pages or from
any static file host.

Run:
  python scripts/generate_preview.py
"""

from __future__ import annotations

import contextlib
import html
import random
import sys
from datetime import date, datetime
from pathlib import Path

from sentinel import DataResidency, Sentinel
from sentinel.compliance import EUAIActChecker
from sentinel.compliance.euaiact import ENFORCEMENT_DATE
from sentinel.dashboard import HTMLReport
from sentinel.manifesto import (
    AcknowledgedGap,
    EUOnly,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
    Targeting,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.scanner import RuntimeScanner
from sentinel.storage import SQLiteStorage

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "preview"


class PreviewPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch = Required()
    storage = OnPremiseOnly(country="EU")
    bsi = Targeting(by="2026-12-31")
    ci_cd = AcknowledgedGap(
        provider="Managed SaaS CI",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign CI alternative with comparable UX today",
    )


def _policy(inputs: dict) -> tuple[bool, str | None]:
    req = inputs.get("request", {})
    if req.get("amount", 0) > 10_000:
        return False, "amount_exceeds_cap"
    return True, None


def _build_sentinel_with_sample_data() -> Sentinel:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="sentinel-preview",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"policies/approval.py": _policy}),
    )

    @sentinel.trace(policy="policies/approval.py")
    def approve(request: dict) -> dict:
        return {"decision": "approved", "amount": request["amount"]}

    rng = random.Random(42)
    for _ in range(200):
        amount = int(rng.triangular(100, 20_000, 5_000))
        with contextlib.suppress(Exception):
            approve(request={"amount": amount, "requester": "sample"})
    return sentinel


def _countdown_days() -> int:
    return (ENFORCEMENT_DATE - date.today()).days


def _svg_gauge(value: float, width: int = 220, height: int = 140) -> str:
    """Render a semicircular gauge as inline SVG (no JS)."""
    value = max(0.0, min(1.0, value))
    cx, cy, r = width / 2, height - 10, 100
    start_x, start_y = cx - r, cy
    end_x, end_y = cx + r, cy
    import math
    angle = math.pi - math.pi * value
    needle_x = cx + r * math.cos(angle)
    needle_y = cy - r * math.sin(angle)
    colour = "#167c3c" if value >= 0.9 else ("#a15c00" if value >= 0.6 else "#a81717")
    return f"""
<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <path d="M {start_x} {start_y} A {r} {r} 0 0 1 {end_x} {end_y}"
        fill="none" stroke="#eee" stroke-width="18"/>
  <path d="M {start_x} {start_y} A {r} {r} 0 0 1 {needle_x} {needle_y}"
        fill="none" stroke="{colour}" stroke-width="18" stroke-linecap="round"/>
  <text x="{cx}" y="{cy - 18}" text-anchor="middle"
        font-family="-apple-system, Segoe UI, sans-serif"
        font-size="30" font-weight="700" fill="{colour}">{value:.0%}</text>
</svg>
""".strip()


def _svg_piechart(slices: list[tuple[str, float, str]], size: int = 220) -> str:
    """Simple pie chart: list of (label, fraction, colour)."""
    import math
    cx, cy, r = size / 2, size / 2, size / 2 - 10
    paths = []
    angle = -math.pi / 2
    for _, fraction, colour in slices:
        if fraction <= 0:
            continue
        next_angle = angle + 2 * math.pi * fraction
        large = 1 if fraction > 0.5 else 0
        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(next_angle)
        y2 = cy + r * math.sin(next_angle)
        path = (
            f'<path d="M {cx} {cy} L {x1:.1f} {y1:.1f} '
            f'A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{colour}"/>'
        )
        paths.append(path)
        angle = next_angle

    legend_items = "".join(
        f'<div style="display:flex;align-items:center;margin:0.2em 0;">'
        f'<span style="display:inline-block;width:12px;height:12px;background:{colour};margin-right:6px;"></span>'
        f'<span style="font-size:0.9em;">{html.escape(label)} ({int(frac * 100)}%)</span>'
        f"</div>"
        for label, frac, colour in slices
        if frac > 0
    )
    return f"""
<div style="display:flex;align-items:center;gap:1em;">
  <svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
    {''.join(paths)}
  </svg>
  <div>{legend_items}</div>
</div>
""".strip()


def _svg_bar_chart(items: list[tuple[str, float, str]], width: int = 420) -> str:
    """Horizontal bar chart with labels."""
    rows = []
    bar_height = 20
    for i, (label, value, colour) in enumerate(items):
        y = i * (bar_height + 10)
        bar_width = int((width - 180) * max(0.0, min(1.0, value)))
        rows.append(
            f'<text x="0" y="{y + 14}" font-size="12" fill="#333">{html.escape(label)}</text>'
            f'<rect x="160" y="{y}" width="{bar_width}" height="{bar_height}" fill="{colour}"/>'
            f'<text x="{160 + bar_width + 6}" y="{y + 14}" font-size="12" fill="#555">{int(value * 100)}%</text>'
        )
    height = len(items) * (bar_height + 10) + 10
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg">{"".join(rows)}</svg>'
    )


def _render_index(
    *,
    sentinel: Sentinel,
    sovereignty_score: float,
    compliance: object,
    days_to_enforcement: int,
) -> str:
    e = html.escape
    traces = sentinel.query(limit=200)
    allow = sum(
        1
        for t in traces
        if t.policy_evaluation and t.policy_evaluation.result.value == "ALLOW"
    )
    deny = sum(
        1
        for t in traces
        if t.policy_evaluation and t.policy_evaluation.result.value == "DENY"
    )
    total = len(traces)
    allow_frac = allow / total if total else 0
    deny_frac = deny / total if total else 0
    other_frac = max(0.0, 1.0 - allow_frac - deny_frac)

    pie = _svg_piechart(
        [
            ("ALLOW", allow_frac, "#167c3c"),
            ("DENY", deny_frac, "#a81717"),
            ("OTHER", other_frac, "#888"),
        ]
    )
    gauge = _svg_gauge(sovereignty_score)

    # Article coverage bar chart
    art_items = []
    for art in ("Art. 9", "Art. 12", "Art. 13", "Art. 14", "Art. 17"):
        a = compliance.articles.get(art)  # type: ignore[attr-defined]
        if a is None:
            continue
        if a.status == "COMPLIANT":
            value, colour = 1.0, "#167c3c"
        elif a.status == "PARTIAL":
            value, colour = 0.5, "#a15c00"
        else:
            value, colour = 0.2, "#a81717"
        art_items.append((f"{art} — {a.title[:28]}", value, colour))
    art_chart = _svg_bar_chart(art_items)

    recent_rows = "".join(
        f"<tr>"
        f"<td>{t.started_at.strftime('%H:%M:%S')}</td>"
        f"<td>{e(t.agent[:30])}</td>"
        f"<td>{(t.policy_evaluation.result.value if t.policy_evaluation else '—')}</td>"
        f"<td>{e(t.sovereign_scope)}</td>"
        f"<td>{e(t.data_residency.value)}</td>"
        f"<td>{t.latency_ms or 0} ms</td>"
        f"</tr>"
        for t in traces[:20]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel — live sovereignty preview</title>
<style>
 :root {{ --fg: #111; --muted: #555; --border: #ddd; --accent: #0052cc; }}
 * {{ box-sizing: border-box; }}
 body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        max-width: 1100px; margin: 2em auto; padding: 0 1em; color: var(--fg); background: #fff; }}
 h1 {{ font-size: 2em; margin-bottom: 0.1em; }}
 h2 {{ font-size: 1.3em; margin-top: 2.2em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
 .lead {{ font-size: 1.05em; color: var(--muted); max-width: 68ch; }}
 .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1em; margin-top: 1em; }}
 .card {{ border: 1px solid var(--border); border-radius: 8px; padding: 1em; background: #fafafa; }}
 .card h3 {{ margin: 0 0 0.4em 0; font-size: 1em; color: var(--muted); }}
 .card .value {{ font-size: 1.6em; font-weight: 700; }}
 pre {{ background: #f6f8fa; border: 1px solid var(--border); border-radius: 6px; padding: 0.8em; overflow-x: auto; font-size: 0.88em; }}
 table {{ border-collapse: collapse; width: 100%; margin-top: 0.6em; font-size: 0.9em; }}
 th, td {{ border: 1px solid var(--border); padding: 0.4em 0.6em; text-align: left; }}
 th {{ background: #f4f4f4; }}
 a {{ color: var(--accent); }}
 .row {{ display: flex; gap: 2em; align-items: center; flex-wrap: wrap; }}
 .install {{ background: #111; color: #fff; padding: 0.6em 0.9em; border-radius: 6px; display: inline-block; font-family: monospace; }}
 footer {{ margin-top: 3em; padding: 1em 0; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.85em; }}
</style>
</head>
<body>

<h1>Sentinel</h1>
<p class="lead">
 EU-sovereign AI decision middleware. Wraps any AI agent, evaluates
 policy in-process, and writes tamper-resistant decision records to
 local storage. Zero dependencies. Air-gapped capable. Apache 2.0.
</p>

<p class="install">pip install sentinel-kernel</p>
&nbsp; &nbsp;
<a href="https://github.com/sebastianweiss83/sentinel-kernel">GitHub</a> ·
<a href="https://pypi.org/project/sentinel-kernel/">PyPI</a> ·
<a href="report.html">Full sample report</a>

<h2>Live sample dashboard</h2>
<p class="lead">
 The charts below are rendered from a sample Sentinel run with 200
 simulated decisions. Every element is inline SVG — zero external
 resources, zero JavaScript. Safe for air-gapped environments.
</p>

<div class="cards">
  <div class="card"><h3>Sovereignty score</h3>{gauge}</div>
  <div class="card">
    <h3>Days to EU AI Act enforcement</h3>
    <div class="value">{days_to_enforcement}</div>
    <div style="color:var(--muted);font-size:0.85em;">2 August 2026 — Annex III</div>
  </div>
  <div class="card">
    <h3>Sample decisions</h3>
    <div class="value">{total}</div>
    <div style="color:var(--muted);font-size:0.85em;">ALLOW: {allow} · DENY: {deny}</div>
  </div>
</div>

<h3 style="margin-top:2em;">Policy result distribution</h3>
{pie}

<h3 style="margin-top:2em;">EU AI Act article coverage</h3>
{art_chart}

<h3 style="margin-top:2em;">Recent decisions</h3>
<table><thead><tr>
 <th>Time</th><th>Agent</th><th>Result</th><th>Scope</th><th>Residency</th><th>Latency</th>
</tr></thead><tbody>{recent_rows}</tbody></table>

<h2>Declare your sovereignty requirements in code</h2>
<pre>from sentinel.manifesto import (
    SentinelManifesto, EUOnly, Required, OnPremiseOnly,
    Targeting, AcknowledgedGap,
)

class OurPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch = Required()
    storage = OnPremiseOnly(country="DE")
    bsi = Targeting(by="2026-12-31")

    ci_cd = AcknowledgedGap(
        provider="Managed SaaS CI",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign CI alternative with comparable UX",
    )

report = OurPolicy().check()
print(report.as_text())</pre>

<h2>Quick demo</h2>
<pre># 2-minute local demo
pip install sentinel-kernel
python -c "
from sentinel import Sentinel
sentinel = Sentinel()

@sentinel.trace
def decide(req):
    return {{'decision': 'approved'}}

decide({{'amount': 5000}})
print(sentinel.query(limit=1)[0].to_json())
"

# Full Grafana + OTel stack (requires Docker)
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel/demo
docker compose up --build</pre>

<h2>What Sentinel answers for you</h2>
<table>
 <tr><th>Question</th><th>Sentinel answer</th></tr>
 <tr><td>What was decided?</td><td>Append-only DecisionTrace with policy result and rule</td></tr>
 <tr><td>By which model, which policy, which version?</td><td>Every trace records agent, model, policy name/version</td></tr>
 <tr><td>Under whose law is the evidence stored?</td><td>sovereign_scope and data_residency on every record</td></tr>
 <tr><td>Can a human halt it?</td><td>Runtime kill switch (Art. 14) with no restart</td></tr>
 <tr><td>What of this am I compliant with today?</td><td>sentinel compliance check</td></tr>
 <tr><td>Where is my sovereignty leaking?</td><td>sentinel scan (runtime + CI/CD + infrastructure)</td></tr>
</table>

<footer>
 Generated {e(datetime.now().isoformat(timespec='seconds'))} ·
 Apache 2.0 ·
 sentinel-kernel ·
 <a href="https://github.com/sebastianweiss83/sentinel-kernel">github.com/sebastianweiss83/sentinel-kernel</a>
</footer>
</body>
</html>
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sentinel = _build_sentinel_with_sample_data()
    sovereignty_score = RuntimeScanner().scan().sovereignty_score
    compliance = EUAIActChecker().check(sentinel)
    days = _countdown_days()

    index_html = _render_index(
        sentinel=sentinel,
        sovereignty_score=sovereignty_score,
        compliance=compliance,
        days_to_enforcement=days,
    )
    (OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

    report_html = HTMLReport().generate(sentinel, manifesto=PreviewPolicy())
    (OUT_DIR / "report.html").write_text(report_html, encoding="utf-8")

    # Also emit a .nojekyll so GitHub Pages serves files as-is
    (OUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Generated {OUT_DIR / 'index.html'}")
    print(f"Generated {OUT_DIR / 'report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
