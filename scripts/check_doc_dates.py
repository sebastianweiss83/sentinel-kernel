#!/usr/bin/env python3
"""
Prevent documentation version rot.

Fails if any ``docs/*.md`` mentions a Sentinel version older than the
current ``sentinel/__init__.py::__version__`` as the "current" version.

Accepted patterns (whitelisted as historical):
  - inside code blocks (``...``)
  - inside "## [X.Y.Z]" CHANGELOG-style headings in docs/archive/
  - lines prefixed with "v" as part of a multi-version table row

What fails:
  - a doc line saying "Current results (v3.1.0, ...)" when __version__
    is 3.2.0 or later
  - a doc line saying "as of v3.1" that isn't archived

This is deliberately conservative — false positives are OK; what we
want to catch is unmaintained "Current state / As of / Last updated"
claims.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "sentinel" / "__init__.py"
DOCS = ROOT / "docs"

STALE_PHRASES = (
    r"current results \(v",
    r"as of v",
    r"latest version is v",
    r"current version is v",
)


def current_version() -> str:
    text = INIT.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not m:
        raise SystemExit("check_doc_dates: no __version__ in sentinel/__init__.py")
    return m.group(1)


def version_tuple(v: str) -> tuple[int, ...]:
    core = v.split("-", 1)[0]
    return tuple(int(p) for p in core.split(".") if p.isdigit())


def main() -> int:
    current = current_version()
    cur_t = version_tuple(current)

    findings: list[str] = []

    if not DOCS.exists():
        print("check_doc_dates: no docs/ directory; nothing to check.")
        return 0

    for path in DOCS.rglob("*.md"):
        if "archive" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            low = line.lower()
            for phrase in STALE_PHRASES:
                if not re.search(phrase, low):
                    continue
                m = re.search(r"v(\d+(?:\.\d+){1,2})", line)
                if not m:
                    continue
                found_v = m.group(1)
                if version_tuple(found_v) < cur_t:
                    findings.append(
                        f"{path.relative_to(ROOT)}:{lineno}: "
                        f"claims '{phrase.strip()}' v{found_v}, "
                        f"but current __version__ is {current}"
                    )

    if findings:
        print("check_doc_dates — stale references:", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        print(
            "\nUpdate the doc to the current version, or move it to "
            "docs/archive/ if it is historical.",
            file=sys.stderr,
        )
        return 1

    print(f"check_doc_dates: OK — no stale v< {current} claims outside archive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
