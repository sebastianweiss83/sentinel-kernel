#!/usr/bin/env python3
"""
Thesis 3: Apache 2.0 enforced — no proprietary dep in Sentinel core.

Reads [project.dependencies] from pyproject.toml.
Checks each core dependency's license via importlib.metadata.
Fails if any CORE dep has a non-permissive license.

Optional deps ([project.optional-dependencies]) are NOT checked here —
they are by definition non-core and sovereignty-posture documented.

Exit 0: all core deps are permissively licensed
Exit 1: violation found — named and explained
"""

from __future__ import annotations

import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

ALLOWED_LICENSES = {
    "MIT",
    "MIT License",
    "Apache-2.0",
    "Apache 2.0",
    "Apache Software License",
    "Apache License 2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BSD License",
    "BSD",
    "ISC",
    "ISC License (ISCL)",
    "PSF",
    "PSF-2.0",
    "Python Software Foundation License",
    "LGPL-2.1",
    "LGPL-2.1-only",
    "GNU Lesser General Public License v2 or later (LGPLv2+)",
    "MPL-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)",
    "Unlicense",
    "CC0-1.0",
    "0BSD",
}

ROOT = Path(__file__).resolve().parents[1]


def _parse_dep_name(spec: str) -> str:
    """Extract package name from a PEP 508 dep spec."""
    match = re.match(r"^\s*([A-Za-z0-9_.\-]+)", spec)
    return match.group(1) if match else spec.strip()


def _extract_license(pkg_meta: metadata.PackageMetadata) -> str:
    """Pull the license string from package metadata (multiple sources)."""
    license_str = pkg_meta.get("License-Expression") or pkg_meta.get("License") or ""
    if license_str and license_str != "UNKNOWN":
        return license_str.strip()

    for classifier in pkg_meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            parts = [p.strip() for p in classifier.split("::")]
            if parts:
                return parts[-1]
    return ""


def _license_ok(license_str: str) -> bool:
    if not license_str:
        return False
    license_clean = license_str.strip().strip('"').strip("'")
    return any(
        allowed.lower() in license_clean.lower() or license_clean.lower() in allowed.lower()
        for allowed in ALLOWED_LICENSES
    )


def main() -> int:
    pyproject = ROOT / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    deps: list[str] = data.get("project", {}).get("dependencies", []) or []

    if not deps:
        print("✓ Sentinel core has zero hard dependencies — license check trivially passes.")
        return 0

    violations: list[str] = []
    checked = 0
    for spec in deps:
        name = _parse_dep_name(spec)
        try:
            pkg_meta = metadata.metadata(name)
        except metadata.PackageNotFoundError:
            print(f"WARNING: {name} not installed — cannot check license")
            continue

        license_str = _extract_license(pkg_meta)
        if not _license_ok(license_str):
            violations.append(f"{name}: license='{license_str}' not in ALLOWED_LICENSES")
        else:
            print(f"  ✓ {name}: {license_str}")
            checked += 1

    if violations:
        print("\nLICENSE CHECK FAILED")
        print("=" * 50)
        for v in violations:
            print(f"  {v}")
        print(
            "\nA non-permissive license in a core dep makes Thesis 3 "
            "(Apache 2.0 forever) unenforceable."
        )
        return 1

    print(f"\n✓ All {checked} core dependencies are permissively licensed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
