#!/usr/bin/env python3
"""
scripts/sync_all.py
~~~~~~~~~~~~~~~~~~~

Single source of truth for all auto-generated content in the repo.

After a push to main (or locally before a push), this script updates:

  1. CLAUDE.md                   — the existing auto-generated state block
  2. README.md                   — badges between SYNC_ALL markers
  3. docs/project-status.md      — full current state, fully regenerated
  4. docs/preview/index.html     — GitHub Pages content

Nothing else is touched. Curated prose stays put.

Usage::

    python scripts/sync_all.py           # updates all four targets
    python scripts/sync_all.py --check   # exit 1 if any would change
    python scripts/sync_all.py --quiet   # no progress output

Contract (from CLAUDE.md):
    Every push to main → CI runs sync_all.py → commits any changes.
    Manual edits to the four targets will be overwritten.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Re-use the existing CLAUDE.md updater
sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_claude_md import (  # noqa: E402
    collect_state,
)
from update_claude_md import (
    render_block as render_claude_block,
)
from update_claude_md import (
    splice as splice_claude,
)

ROOT = Path(__file__).resolve().parents[1]

CLAUDE_MD = ROOT / "CLAUDE.md"
README = ROOT / "README.md"
STATUS = ROOT / "docs" / "project-status.md"
PREVIEW_DIR = ROOT / "docs" / "preview"

README_START = "<!-- SYNC_ALL_README_START -->"
README_END = "<!-- SYNC_ALL_README_END -->"

STATUS_START = "<!-- SYNC_ALL_STATUS_START -->"
STATUS_END = "<!-- SYNC_ALL_STATUS_END -->"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, check=False
        )
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _splice(original: str, start: str, end: str, new_block: str) -> str:
    """Replace the content between ``start`` and ``end`` markers.

    Raises RuntimeError if the markers are missing — the human has
    edited the target to remove them and needs to put them back.
    """
    si = original.find(start)
    ei = original.find(end)
    if si == -1 or ei == -1 or ei < si:
        raise RuntimeError(
            f"Missing sync markers {start!r} / {end!r}. Restore them before "
            "running sync_all.py."
        )
    before = original[: si + len(start)]
    after = original[ei:]
    return f"{before}\n{new_block}\n{after}"


def _read_description() -> str:
    """Read the project description from pyproject.toml."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^description\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "Sovereign decision tracing for any autonomous system."


def _read_module_coverage() -> list[tuple[str, int]]:
    """Return [(module_path, coverage_pct)] from a pytest --cov run.

    Sorted by module path. Returns [] if pytest can't be run.
    """
    out = _run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"])
    rows: list[tuple[str, int]] = []
    # Coverage table lines look like:
    #   sentinel/core/trace.py    119    0   100%
    for line in out.splitlines():
        m = re.match(r"^(sentinel/[^\s]+\.py)\s+\d+\s+\d+\s+(\d+)%", line)
        if m:
            rows.append((m.group(1), int(m.group(2))))
    rows.sort()
    return rows


def _read_recent_releases(limit: int = 10) -> list[tuple[str, str]]:
    """Return [(tag, title)] of the most recent GitHub releases."""
    out = _run([
        "gh",
        "release",
        "list",
        "--limit",
        str(limit),
    ])
    releases: list[tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        title = parts[0].strip()
        # gh release list format: title \t type \t tag \t date
        tag = parts[2].strip() if len(parts) >= 3 else ""
        if tag:
            releases.append((tag, title))
    return releases


def _read_roadmap_from_changelog() -> list[tuple[str, str]]:
    """Return the list of shipped versions and the 1-line summary for each."""
    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        return []
    text = changelog.read_text(encoding="utf-8")
    # Match headers like "## [1.2.3] — YYYY-MM-DD" and grab the first non-blank
    # line underneath as the summary.
    versions: list[tuple[str, str]] = []
    for m in re.finditer(
        r"^## \[([^\]]+)\] — (\d{4}-\d{2}-\d{2})\n\n([^\n]+)",
        text,
        re.MULTILINE,
    ):
        version = m.group(1)
        summary = m.group(3).strip()
        if version.lower() != "unreleased":
            versions.append((f"{version} ({m.group(2)})", summary))
    return versions[:12]


def _read_feature_list() -> list[str]:
    """Read exported names from key modules to produce a feature bullet list."""
    features: list[str] = []

    # Sentinel core
    features.append("`Sentinel` class with `@sentinel.trace` decorator")
    features.append("`Sentinel.verify_integrity(trace_id)` — recomputable SHA-256 evidence")
    features.append("`Sentinel.engage_kill_switch(reason)` — EU AI Act Art. 14 halt")

    # Storage
    features.append("SQLite / Filesystem / PostgreSQL append-only backends")
    features.append("NDJSON `export_ndjson` / `import_ndjson` with filters")
    features.append("`purge_before(cutoff, dry_run)` retention management")

    # Manifesto
    mani = (ROOT / "sentinel" / "manifesto" / "__init__.py").read_text(encoding="utf-8")
    mani_types = re.findall(r'"(\w+)",', mani)
    if mani_types:
        types = ", ".join(f"`{t}`" for t in sorted(mani_types) if t[0].isupper())
        features.append(f"Manifesto types: {types}")

    # Compliance
    comp = (ROOT / "sentinel" / "compliance" / "__init__.py").read_text(encoding="utf-8")
    checkers = re.findall(r'"(\w*Checker)"', comp)
    if checkers:
        features.append(
            "Compliance checkers: " + ", ".join(f"`{c}`" for c in sorted(set(checkers)))
        )

    # Integrations
    integrations_dir = ROOT / "sentinel" / "integrations"
    names = sorted(
        p.stem for p in integrations_dir.glob("*.py") if p.stem != "__init__"
    )
    if names:
        features.append(
            "Integrations: " + ", ".join(f"`{n}`" for n in names)
        )

    return features


# ---------------------------------------------------------------------------
# Target 1: CLAUDE.md
# ---------------------------------------------------------------------------


def update_claude_md(state: dict) -> bool:
    """Return True if CLAUDE.md was modified."""
    original = CLAUDE_MD.read_text(encoding="utf-8")
    block = render_claude_block(**state)  # type: ignore[arg-type]
    updated = splice_claude(original, block)
    if updated != original:
        CLAUDE_MD.write_text(updated, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------------------
# Target 2: README.md badges
# ---------------------------------------------------------------------------


def _render_readme_block(state: dict) -> str:
    version = state["version"]
    test_count = re.sub(r"\D", "", str(state["tests"])) or "unknown"
    coverage = str(state["coverage"]).replace("%", "")

    # URL-encode spaces etc. shields.io handles URL-encoding for simple tokens,
    # so we keep the scheme predictable by using dashes rather than spaces.
    lines = [
        "[![PyPI](https://img.shields.io/pypi/v/sentinel-kernel)]"
        "(https://pypi.org/project/sentinel-kernel/)",
        f"[![Version](https://img.shields.io/badge/version-v{version}-blue)]"
        "(CHANGELOG.md)",
        "[![License](https://img.shields.io/badge/license-Apache%202.0-blue)]"
        "(https://www.apache.org/licenses/LICENSE-2.0)",
        f"[![Tests](https://img.shields.io/badge/tests-{test_count}%20passing-brightgreen)]"
        "(https://github.com/sebastianweiss83/sentinel-kernel/actions)",
        f"[![Coverage](https://img.shields.io/badge/coverage-{coverage}%25-brightgreen)]"
        "(https://github.com/sebastianweiss83/sentinel-kernel/actions)",
        "[![Status](https://img.shields.io/badge/status-production%2Fstable-brightgreen)]"
        "(CHANGELOG.md)",
        "[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%2012%2F13%2F14%2F17-green)]"
        "(docs/eu-ai-act.md)",
    ]
    return "\n".join(lines)


def update_readme(state: dict) -> bool:
    """Return True if README.md was modified."""
    on_disk = README.read_text(encoding="utf-8")
    block = _render_readme_block(state)

    working = on_disk
    # If markers are missing, insert them around the existing badge block.
    if README_START not in working:
        lines = working.splitlines()
        first = None
        last = None
        for i, line in enumerate(lines):
            if line.startswith("[!["):
                if first is None:
                    first = i
                last = i
            elif first is not None and line.strip() == "":
                # allow single blank lines inside the block
                continue
            elif first is not None:
                break
        if first is None or last is None:
            raise RuntimeError(
                f"README.md has no badge block and no {README_START} markers."
            )
        # Replace the existing block with marker-wrapped generated block.
        lines[first:last + 1] = [README_START, block, README_END]
        working = "\n".join(lines) + ("\n" if not on_disk.endswith("\n") or True else "")
    else:
        working = _splice(working, README_START, README_END, block)

    if working != on_disk:
        README.write_text(working, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------------------
# Target 3: docs/project-status.md
# ---------------------------------------------------------------------------


def _render_status_block(state: dict) -> str:
    version = state["version"]
    tests = state["tests"]
    coverage = state["coverage"]
    smoke = state["smoke"]
    description = _read_description()
    module_coverage = _read_module_coverage()
    releases = _read_recent_releases(limit=12)
    roadmap = _read_roadmap_from_changelog()
    features = _read_feature_list()
    issues = state["issues"]

    lines: list[str] = []
    lines.append(f"_Last generated from HEAD commit: {state['last_updated']}_")
    lines.append("")

    # Version section
    lines.append("## Version")
    lines.append("")
    lines.append(f"**`{version}`** — Production/Stable")
    lines.append("")
    lines.append(description)
    lines.append("")

    # Health
    lines.append("## Test suite")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| Tests | {tests} |")
    lines.append(f"| Coverage | {coverage} |")
    lines.append(f"| Smoke test | {smoke} |")
    lines.append("")

    # Modules coverage
    if module_coverage:
        lines.append("## Modules")
        lines.append("")
        lines.append("| Module | Coverage | Status |")
        lines.append("|---|---|---|")
        for module, pct in module_coverage:
            icon = "✓" if pct >= 95 else ("~" if pct >= 80 else "✗")
            lines.append(f"| `{module}` | {pct}% | {icon} |")
        lines.append("")

    # Features
    lines.append("## What's inside")
    lines.append("")
    for f in features:
        lines.append(f"- {f}")
    lines.append("")

    # Open issues
    lines.append("## Open issues")
    lines.append("")
    if issues is None:
        lines.append("_gh CLI unavailable — this section is refreshed in CI_")
    elif not issues:
        lines.append("_no open issues_ 🎉")
    else:
        for number, title, labels in issues:
            label_suffix = f" _(labels: {', '.join(labels)})_" if labels else ""
            lines.append(f"- **#{number}** {title}{label_suffix}")
    lines.append("")

    # Recent releases
    if releases:
        lines.append("## Recent releases")
        lines.append("")
        for tag, title in releases:
            lines.append(f"- **{tag}** — {title}")
        lines.append("")

    # Roadmap / shipped
    if roadmap:
        lines.append("## Shipped")
        lines.append("")
        for version_line, summary in roadmap:
            lines.append(f"- **{version_line}** — {summary}")
        lines.append("")

    return "\n".join(lines)


_STATUS_TEMPLATE = """# Sentinel — Project Status

> ⚠️ **Auto-generated by `scripts/sync_all.py`.**
> Do not edit manually — changes will be overwritten by CI on the
> next push to `main`. To update: push to `main`, or run
> `python scripts/sync_all.py` locally and commit the result.

{start}
{body}
{end}
"""


def update_project_status(state: dict) -> bool:
    """Return True if docs/project-status.md was modified."""
    block = _render_status_block(state)

    original = STATUS.read_text(encoding="utf-8") if STATUS.exists() else ""

    if STATUS_START not in original or STATUS_END not in original:
        # Initial creation (or migration): stomp the file entirely.
        new_content = _STATUS_TEMPLATE.format(
            start=STATUS_START,
            body=block,
            end=STATUS_END,
        )
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        if original != new_content:
            STATUS.write_text(new_content, encoding="utf-8")
            return True
        return False

    updated = _splice(original, STATUS_START, STATUS_END, block)
    if updated != original:
        STATUS.write_text(updated, encoding="utf-8")
        return True
    return False


# ---------------------------------------------------------------------------
# Target 4: docs/preview/index.html
# ---------------------------------------------------------------------------


def update_preview() -> bool:
    """Regenerate docs/preview/ via scripts/generate_preview.py.

    Returns True if any file in docs/preview/ changed.
    """
    before: dict[Path, bytes] = {}
    if PREVIEW_DIR.exists():
        for p in PREVIEW_DIR.rglob("*"):
            if p.is_file():
                before[p] = p.read_bytes()

    out = _run([sys.executable, str(ROOT / "scripts" / "generate_preview.py")])
    # If the script failed silently, the directory may still be fine.
    del out  # informational only

    if not PREVIEW_DIR.exists():
        return False

    after: dict[Path, bytes] = {}
    for p in PREVIEW_DIR.rglob("*"):
        if p.is_file():
            after[p] = p.read_bytes()

    return before != after


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update all auto-generated content from the current repo state.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report what would change without writing. Exit 1 if stale.",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress progress output."
    )
    parser.add_argument(
        "--skip-preview",
        action="store_true",
        help="Skip the generate_preview.py regeneration step.",
    )
    args = parser.parse_args(argv)

    def say(msg: str) -> None:
        if not args.quiet:
            print(msg)

    say("Reading repository state...")
    state = collect_state()
    say(
        f"  version={state['version']} tests={state['tests']} "
        f"coverage={state['coverage']} smoke={state['smoke']}"
    )

    # In --check mode: compute diffs without writing. Simplest approach:
    # snapshot the files, run, compare, restore.
    if args.check:
        snapshots: dict[Path, bytes | None] = {}
        targets = [CLAUDE_MD, README, STATUS]
        for t in targets:
            snapshots[t] = t.read_bytes() if t.exists() else None
        preview_before: dict[Path, bytes] = {}
        if PREVIEW_DIR.exists():
            for p in PREVIEW_DIR.rglob("*"):
                if p.is_file():
                    preview_before[p] = p.read_bytes()

    changed: dict[str, bool] = {}
    try:
        changed["CLAUDE.md"] = update_claude_md(state)
    except RuntimeError as exc:
        say(f"  CLAUDE.md: {exc}")
        return 2

    try:
        changed["README.md"] = update_readme(state)
    except RuntimeError as exc:
        say(f"  README.md: {exc}")
        return 2

    changed["docs/project-status.md"] = update_project_status(state)

    if args.skip_preview:
        changed["docs/preview/"] = False
    else:
        changed["docs/preview/"] = update_preview()

    if args.check:
        any_changed = any(changed.values())
        for target, did_change in changed.items():
            marker = "STALE" if did_change else "ok"
            say(f"  {target}: {marker}")
        # Restore targets so --check is non-destructive
        for t, blob in snapshots.items():
            if blob is None and t.exists():
                t.unlink()
            elif blob is not None:
                t.write_bytes(blob)
        # Restore preview
        if PREVIEW_DIR.exists():
            for p in PREVIEW_DIR.rglob("*"):
                if p.is_file() and p not in preview_before:
                    p.unlink(missing_ok=True)
            for p, data in preview_before.items():
                p.write_bytes(data)
        return 1 if any_changed else 0

    # Normal mode: report and return.
    for target, did_change in changed.items():
        icon = "✓" if did_change else "·"
        verb = "updated" if did_change else "unchanged"
        say(f"  {icon} {target} {verb}")

    if any(changed.values()):
        say("")
        say("Run `git diff` to review, then commit.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
