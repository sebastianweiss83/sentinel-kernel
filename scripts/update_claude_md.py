#!/usr/bin/env python3
"""
scripts/update_claude_md.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Read the actual repository state and rewrite the auto-generated block
inside ``CLAUDE.md`` with the current truth. The script never touches
the curated prose above and below the sentinel markers.

Sources of truth:
    version       pyproject.toml  ->  [project].version
    tests         pytest tests/ -q  ->  "N passed" summary
    coverage      pytest --cov output  ->  "TOTAL ... XX%"
    last commits  git log -5 --pretty=...
    open issues   gh issue list --state open --json number,title,labels

Anything that cannot be determined (for example, ``gh`` unauthenticated
in a fresh clone) degrades to "unknown" rather than crashing. This is
deliberate: the script is used from a CI workflow that must never fail
the pipeline just because telemetry is missing.

Usage::

    python scripts/update_claude_md.py
    python scripts/update_claude_md.py --check   # exit 1 if a rewrite is needed

The script is idempotent: running it twice in a row on the same state
produces the same file byte-for-byte.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = ROOT / "CLAUDE.md"
PYPROJECT = ROOT / "pyproject.toml"

START_MARKER = "<!-- CLAUDE_MD_AUTO_START -->"
END_MARKER = "<!-- CLAUDE_MD_AUTO_END -->"


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------


def _run(cmd: list[str], *, check: bool = False) -> str:
    try:
        out = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=check,
        )
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def read_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def read_tests_and_coverage() -> tuple[str, str]:
    """Run pytest once and parse both the pass count and TOTAL coverage.

    Invoked via ``sys.executable -m pytest`` so the subprocess always
    uses the exact Python interpreter running this script — avoiding
    PATH lookups that fail when the caller (e.g. ``.venv/bin/python
    scripts/sync_all.py``) has not activated the venv.
    """
    out = _run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"])
    tests = "unknown"
    coverage = "unknown"

    # "N passed" or "N passed, M warnings in S s"
    m = re.search(r"(\d+)\s+passed", out)
    if m:
        tests = f"{m.group(1)} passing"

    # Coverage table footer. With --cov-branch the TOTAL row has five
    # numeric columns (statements, missing, branches, partial, coverage%);
    # without it the row has three. Match either shape by consuming one
    # or more whitespace+integer groups before the final coverage cell.
    cov = re.search(r"^TOTAL(?:\s+\d+)+\s+(\d+)%", out, re.MULTILINE)
    if cov:
        coverage = f"{cov.group(1)}%"

    return tests, coverage


def read_smoke_test() -> str:
    """Run the smoke test and report N/N or 'failed at step N'.

    Invoked via ``sys.executable`` for the same reason as
    :func:`read_tests_and_coverage` — the interpreter running this
    script is authoritative.
    """
    out = _run([sys.executable, "examples/smoke_test.py"])
    passed = re.search(r"ALL (\d+) STEPS PASSED", out)
    if passed:
        n = passed.group(1)
        return f"{n}/{n} \u2713"
    fail = re.search(r"FAILED at step (\d+)", out)
    if fail:
        return f"failed at step {fail.group(1)}"
    # Count green ticks as a best-effort fallback
    steps = len(re.findall(r"\[\u2713\] Step \d+", out))
    if steps:
        return f"{steps}/{steps}"
    return "unknown"


def read_last_commits(n: int = 5) -> list[tuple[str, str]]:
    """Return the last ``n`` commits as (sha, subject) pairs.

    Filters out auto-sync chore commits (``chore(auto):``) so the
    rendered block is stable across repeated sync runs — otherwise
    every CI sync commit would shift the "last 5 commits" view by one
    and trigger an infinite cascade of trivial drift.
    """
    # Pull a wider window so we still have n non-auto commits after filtering.
    out = _run(["git", "log", f"-{n * 4}", "--pretty=format:%h|%s"])
    pairs: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        sha, subject = line.split("|", 1)
        subject = subject.strip()
        if subject.startswith("chore(auto):"):
            continue
        pairs.append((sha.strip(), subject))
        if len(pairs) >= n:
            break
    return pairs


def read_head_commit_date() -> str:
    """Return the most recent non-auto commit's date as the stamp.

    We skip ``chore(auto):`` commits so that an auto-sync commit does
    not keep shifting the "last updated" field, which would otherwise
    make every subsequent run produce new drift.
    """
    # Ask git for the latest N commits and pick the first non-auto one.
    out = _run(["git", "log", "-20", "--pretty=format:%s||%cs %cI"])
    for line in out.splitlines():
        if "||" not in line:
            continue
        subject, rest = line.split("||", 1)
        if subject.startswith("chore(auto):"):
            continue
        parts = rest.strip().split()
        if not parts:
            continue
        short_date = parts[0]
        iso = parts[1] if len(parts) > 1 else ""
        time_part = iso.split("T", 1)[1] if "T" in iso else ""
        hhmm = time_part[:5] if len(time_part) >= 5 else ""
        return f"{short_date} {hhmm} UTC".strip()
    return "unknown"


def read_open_issues() -> list[tuple[int, str, list[str]]] | None:
    """Return open issues via ``gh``. Returns None if gh is unavailable."""
    out = _run(
        [
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            "50",
            "--json",
            "number,title,labels",
        ]
    )
    if not out.strip():
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    issues: list[tuple[int, str, list[str]]] = []
    for item in data:
        number = int(item.get("number", 0))
        title = str(item.get("title", ""))
        labels = [lbl.get("name", "") for lbl in item.get("labels", [])]
        issues.append((number, title, labels))
    issues.sort(key=lambda x: x[0])
    return issues


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_block(
    *,
    version: str,
    tests: str,
    coverage: str,
    smoke: str,
    last_updated: str,
    commits: list[tuple[str, str]],
    issues: list[tuple[int, str, list[str]]] | None,
) -> str:
    """Build the full content for the auto-generated block.

    Does not include the sentinel markers themselves — the caller splices
    this text between them.
    """
    lines: list[str] = []
    lines.append("")
    lines.append(
        "<!-- This block is rewritten by scripts/update_claude_md.py. "
        "Do not edit by hand. -->"
    )
    lines.append("")
    lines.append("## Current state")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| Version | `{version}` |")
    lines.append(f"| Tests | {tests} |")
    lines.append(f"| Coverage | {coverage} |")
    lines.append(f"| Smoke test | {smoke} |")
    lines.append(f"| Last updated | {last_updated} |")
    lines.append("")

    lines.append("## Last 5 commits")
    lines.append("")
    if commits:
        for sha, subject in commits:
            lines.append(f"- `{sha}` {subject}")
    else:
        lines.append("_no commits found_")
    lines.append("")

    lines.append("## Open issues")
    lines.append("")
    if issues is None:
        lines.append(
            "_gh CLI unavailable or unauthenticated — run locally "
            "`gh auth login` to populate this section_"
        )
    elif not issues:
        lines.append("_no open issues_ \U0001f389")
    else:
        for number, title, labels in issues:
            label_suffix = f" _(labels: {', '.join(labels)})_" if labels else ""
            lines.append(f"- **#{number}** {title}{label_suffix}")
    lines.append("")

    return "\n".join(lines)


def splice(original: str, new_block: str) -> str:
    """Replace the text between the two sentinel markers in ``original``.

    Raises ``RuntimeError`` if the markers are missing — that means
    CLAUDE.md has been edited to remove them, which is a structural
    error the human must fix.
    """
    start = original.find(START_MARKER)
    end = original.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise RuntimeError(
            "CLAUDE.md is missing the auto-generation markers "
            f"({START_MARKER} / {END_MARKER}). Restore them before "
            "running this script."
        )
    before = original[: start + len(START_MARKER)]
    after = original[end:]
    return f"{before}\n{new_block}\n{after}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def collect_state() -> dict[str, object]:
    version = read_version()
    tests, coverage = read_tests_and_coverage()
    smoke = read_smoke_test()
    commits = read_last_commits(5)
    issues = read_open_issues()
    last_updated = read_head_commit_date()
    return {
        "version": version,
        "tests": tests,
        "coverage": coverage,
        "smoke": smoke,
        "last_updated": last_updated,
        "commits": commits,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite the auto-generated block in CLAUDE.md "
        "with the current repository state.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if CLAUDE.md would change.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
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

    new_block = render_block(**state)  # type: ignore[arg-type]

    original = CLAUDE_MD.read_text(encoding="utf-8")
    updated = splice(original, new_block)

    if updated == original:
        say("CLAUDE.md already up to date.")
        return 0

    if args.check:
        say("CLAUDE.md is out of date. Run without --check to update.")
        return 1

    CLAUDE_MD.write_text(updated, encoding="utf-8")
    say(f"Wrote {CLAUDE_MD.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
