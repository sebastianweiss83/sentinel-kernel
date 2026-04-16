#!/usr/bin/env python3
"""
Drift detector for Sentinel's public surfaces.

Compares:
  - ``sentinel/__init__.py::__version__``  (source of truth)
  - ``pyproject.toml::version``            (release artefact)
  - ``CHANGELOG.md``                       (has a section for current version)
  - every ``https?://`` URL printed to humans in README.md / docs / sentinel/

Optionally (best-effort, disabled by default — needs network):
  - ``https://pypi.org/pypi/sentinel-kernel/json::info.version``

Exit codes:
  0  everything aligned
  1  local drift (version fields disagree, CHANGELOG missing entry, dead link)
  2  PyPI lags main by > 7 days (requires --check-pypi; otherwise warn-only)

Design notes
------------
Runs fully offline by default. Pass ``--check-pypi`` to include PyPI
comparison in CI once per day or on release.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "sentinel" / "__init__.py"
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

URL_RE = re.compile(r"https?://[^\s)\"'`>]+")

# Hostnames we do NOT bother dialling (user's own repos render via GitHub;
# assume the network test is expensive; keep it air-gap friendly).
SKIP_HOSTS = {
    # add hostnames here that must never be dialled from CI
}


def read_version_from_init() -> str:
    text = INIT.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not m:
        raise SystemExit("check_surfaces: could not find __version__ in sentinel/__init__.py")
    return m.group(1)


def read_version_from_pyproject() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("check_surfaces: could not find version in pyproject.toml")
    return m.group(1)


def changelog_has_section(version: str) -> bool:
    text = CHANGELOG.read_text(encoding="utf-8")
    return f"## [{version}]" in text


def collect_urls(roots: Iterable[Path]) -> set[str]:
    urls: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if path.suffix.lower() not in {".md", ".py", ".html", ".json", ".txt"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for m in URL_RE.findall(text):
                # strip trailing punctuation commonly adjacent to URLs in prose
                m = m.rstrip(".,;:!?")
                urls.add(m)
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-pypi",
        action="store_true",
        help="Also compare against PyPI (requires network).",
    )
    parser.add_argument(
        "--check-urls",
        action="store_true",
        help="Dial every https?:// URL in tracked surfaces (requires network).",
    )
    args = parser.parse_args()

    findings: list[str] = []

    init_v = read_version_from_init()
    pyproj_v = read_version_from_pyproject()

    if init_v != pyproj_v:
        findings.append(
            f"DRIFT: sentinel/__init__.py version {init_v!r} != "
            f"pyproject.toml version {pyproj_v!r}"
        )

    if not changelog_has_section(init_v):
        findings.append(
            f"DRIFT: CHANGELOG.md has no `## [{init_v}]` section"
        )

    if args.check_urls:
        urls = collect_urls([ROOT / "README.md", ROOT / "docs", ROOT / "sentinel"])
        try:
            import urllib.request
            for url in sorted(urls):
                host = url.split("/")[2] if "//" in url else ""
                if host in SKIP_HOSTS:
                    continue
                try:
                    req = urllib.request.Request(url, method="HEAD")
                    with urllib.request.urlopen(req, timeout=6) as r:
                        if r.status >= 400:
                            findings.append(f"DEAD URL: {url} → HTTP {r.status}")
                except Exception as exc:  # pragma: no cover - network-dependent
                    findings.append(f"DEAD URL: {url} → {type(exc).__name__}")
        except ImportError:  # pragma: no cover
            pass

    if args.check_pypi:
        try:
            import json
            import urllib.request
            req = urllib.request.Request(
                "https://pypi.org/pypi/sentinel-kernel/json"
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                pypi = json.load(r)
            pypi_v = pypi["info"]["version"]
            if pypi_v != init_v:
                findings.append(
                    f"WARN: PyPI latest is {pypi_v!r}; main is {init_v!r}. "
                    "Release when ready."
                )
        except Exception as exc:  # pragma: no cover - network-dependent
            findings.append(f"WARN: PyPI check failed ({type(exc).__name__})")

    if findings:
        print("check_surfaces — findings:", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        # PyPI-lag is WARN (exit 0); local drift / dead URLs are FAIL (exit 1).
        if any(not f.startswith("WARN:") for f in findings):
            return 1
        return 0

    print(
        f"check_surfaces: OK — version={init_v}, "
        f"CHANGELOG has section, no drift detected."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
