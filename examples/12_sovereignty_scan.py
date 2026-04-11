"""
12 — Sovereignty scan (runtime / CI/CD / infrastructure).

Inventories the current Python environment, the repository's CI/CD
configuration, and any infrastructure-as-code files, and classifies
every finding by parent-company jurisdiction.

Run:
    python examples/12_sovereignty_scan.py
    python examples/12_sovereignty_scan.py --json
"""

from __future__ import annotations

import json
import sys

from sentinel.scanner import (
    CICDScanner,
    InfrastructureScanner,
    RuntimeScanner,
)


def main() -> int:
    as_json = "--json" in sys.argv[1:]

    runtime = RuntimeScanner().scan()
    cicd = CICDScanner().scan(".")
    infra = InfrastructureScanner().scan(".")

    if as_json:
        out = {
            "runtime": runtime.to_dict(),
            "cicd": cicd.to_dict(),
            "infrastructure": infra.to_dict(),
        }
        print(json.dumps(out, indent=2))
        return 0

    print("RUNTIME")
    print("-------")
    print(f"  packages         : {runtime.total_packages}")
    print(f"  sovereignty score: {runtime.sovereignty_score:.0%}")
    print(f"  us-owned         : {runtime.us_owned_packages}")
    print(f"  unknown          : {runtime.unknown_jurisdiction}")
    if runtime.critical_path_violations:
        print("  CRITICAL PATH VIOLATIONS:")
        for v in runtime.critical_path_violations:
            print(f"    - {v}")
    print()

    print("CI/CD")
    print("-----")
    print(f"  files scanned      : {cicd.files_scanned}")
    print(f"  total findings     : {len(cicd.findings)}")
    print(f"  us-controlled comps: {cicd.us_controlled_components}")
    for f in cicd.findings[:5]:
        print(f"    {f.file:32s} {f.vendor} ({f.jurisdiction})")
    print()

    print("INFRASTRUCTURE")
    print("--------------")
    print(f"  files scanned     : {infra.files_scanned}")
    print(f"  total findings    : {len(infra.findings)}")
    print(f"  us-controlled comps: {infra.us_controlled_components}")
    for f in infra.findings[:5]:
        print(f"    {f.file:32s} {f.vendor} ({f.jurisdiction})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
