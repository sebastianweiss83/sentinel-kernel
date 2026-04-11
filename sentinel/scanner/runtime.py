"""
sentinel.scanner.runtime
~~~~~~~~~~~~~~~~~~~~~~~~
Inspect the installed Python environment and classify packages by
parent-company jurisdiction.

Output is deliberately conservative. Packages with no entry in the
knowledge base are reported as ``Unknown`` rather than assumed safe.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from importlib import metadata as importlib_metadata
from typing import Any

from sentinel.scanner.knowledge import (
    PACKAGE_KNOWLEDGE,
    lookup,
    suggest_alternative,
)


@dataclass
class PackageReport:
    name: str
    version: str
    parent_company: str
    jurisdiction: str
    cloud_act_exposure: bool
    in_critical_path: bool
    is_optional: bool  # True if the package is a sentinel-kernel optional extra

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScanResult:
    packages: list[PackageReport] = field(default_factory=list)
    critical_path_violations: list[str] = field(default_factory=list)

    @property
    def total_packages(self) -> int:
        return len(self.packages)

    @property
    def sovereign_packages(self) -> int:
        return sum(1 for p in self.packages if not p.cloud_act_exposure)

    @property
    def us_owned_packages(self) -> int:
        return sum(1 for p in self.packages if p.jurisdiction == "US")

    @property
    def unknown_jurisdiction(self) -> int:
        return sum(1 for p in self.packages if p.jurisdiction == "Unknown")

    @property
    def sovereignty_score(self) -> float:
        """Ratio of packages with no CLOUD Act exposure, 0.0 – 1.0."""
        if not self.packages:
            return 1.0
        return self.sovereign_packages / self.total_packages

    def sovereign_alternatives(self) -> dict[str, str]:
        """For each US-owned package in the scan, return an EU alternative.

        Returns a ``{package_name: suggestion}`` mapping. Packages with no
        known alternative are omitted.
        """
        out: dict[str, str] = {}
        for p in self.packages:
            if not p.cloud_act_exposure:
                continue
            alt = suggest_alternative(p.name)
            if alt:
                out[p.name] = alt
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_packages": self.total_packages,
            "sovereign_packages": self.sovereign_packages,
            "us_owned_packages": self.us_owned_packages,
            "unknown_jurisdiction": self.unknown_jurisdiction,
            "sovereignty_score": round(self.sovereignty_score, 3),
            "critical_path_violations": self.critical_path_violations,
            "packages": [p.to_dict() for p in self.packages],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# Sentinel's own optional extras — these are fine to be installed,
# but must never end up in the critical path.
_SENTINEL_OPTIONAL_EXTRAS = {
    "psycopg2-binary", "psycopg2",
    "langchain-core", "langchain",
    "langsmith",  # transitively pulled by langchain/langfuse — never in critical path
    "opentelemetry-sdk", "opentelemetry-exporter-otlp",
    "opentelemetry-exporter-otlp-proto-grpc", "opentelemetry-api",
    "langfuse",
}


class RuntimeScanner:
    """
    Scan the running Python environment for sovereignty posture.

    Usage::

        scanner = RuntimeScanner()
        result = scanner.scan()
        print(f"Sovereignty score: {result.sovereignty_score:.0%}")
    """

    def __init__(
        self,
        *,
        knowledge: dict[str, Any] | None = None,
        installed_packages: list[tuple[str, str]] | None = None,
    ) -> None:
        """
        :param knowledge: override the knowledge base (tests only).
        :param installed_packages: list of (name, version). If None, use
            ``importlib.metadata.distributions()``. Injection makes tests
            fully deterministic.
        """
        self._knowledge = knowledge if knowledge is not None else PACKAGE_KNOWLEDGE
        self._installed = installed_packages

    def scan(self) -> ScanResult:
        result = ScanResult()
        for name, version in self._iter_installed():
            report = self._classify(name, version)
            result.packages.append(report)
            if report.in_critical_path and report.cloud_act_exposure:
                result.critical_path_violations.append(
                    f"{report.name} ({report.parent_company}, {report.jurisdiction})"
                )
        return result

    def _iter_installed(self) -> list[tuple[str, str]]:
        if self._installed is not None:
            return list(self._installed)
        out: list[tuple[str, str]] = []
        for dist in importlib_metadata.distributions():
            name = dist.metadata["Name"]
            if not name:
                continue
            out.append((name, dist.version or "unknown"))
        return out

    def _classify(self, name: str, version: str) -> PackageReport:
        info = lookup(name)
        is_optional = name.lower().replace("_", "-") in _SENTINEL_OPTIONAL_EXTRAS

        if info is None:
            return PackageReport(
                name=name,
                version=version,
                parent_company="Unknown",
                jurisdiction="Unknown",
                cloud_act_exposure=False,
                in_critical_path=False,
                is_optional=is_optional,
            )

        in_critical_path = info.typically_critical_path and not is_optional

        return PackageReport(
            name=name,
            version=version,
            parent_company=info.parent_company,
            jurisdiction=info.jurisdiction,
            cloud_act_exposure=info.cloud_act_exposure,
            in_critical_path=in_critical_path,
            is_optional=is_optional,
        )
