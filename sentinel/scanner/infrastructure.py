"""
sentinel.scanner.infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Scan infrastructure-as-code and deployment config for sovereign
posture. We read files as text, we do not execute them.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InfraFinding:
    file: str
    component: str
    vendor: str
    jurisdiction: str
    cloud_act_exposure: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InfraScanResult:
    findings: list[InfraFinding] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def us_controlled_components(self) -> int:
        return sum(1 for f in self.findings if f.jurisdiction == "US")

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_scanned": self.files_scanned,
            "total_findings": len(self.findings),
            "us_controlled_components": self.us_controlled_components,
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


_TF_PROVIDER_RE = re.compile(r'^\s*provider\s+"([^"]+)"', re.MULTILINE)
_K8S_STORAGE_CLASS_RE = re.compile(r"storageClassName:\s*(\S+)")


class InfrastructureScanner:
    """
    Scan infrastructure configuration for cloud provider dependencies.

    Detects:
      - Terraform provider "aws" / "azurerm" / "google" blocks
      - Kubernetes manifests with cloud-specific storage classes
      - .env files referencing cloud endpoints (we warn, we never print values)
    """

    def scan(self, repo_root: str | Path = ".") -> InfraScanResult:
        root = Path(repo_root)
        result = InfraScanResult()

        for tf in sorted(root.rglob("*.tf")):
            if _is_excluded(tf, root):
                continue
            result.files_scanned += 1
            for finding in _scan_terraform(tf, root):
                result.findings.append(finding)

        for yaml_path in sorted(root.rglob("*.yaml")):
            if _is_excluded(yaml_path, root):
                continue
            if not _looks_like_k8s(yaml_path):
                continue
            result.files_scanned += 1
            for finding in _scan_k8s(yaml_path, root):
                result.findings.append(finding)

        env_path = root / ".env"
        if env_path.exists():
            result.files_scanned += 1
            for finding in _scan_env_file(env_path, root):
                result.findings.append(finding)

        return result


def _is_excluded(path: Path, root: Path) -> bool:
    parts = path.resolve().relative_to(root.resolve()).parts
    excluded = {".venv", "venv", ".git", "node_modules", ".tox", "dist", "build"}
    return any(p in excluded for p in parts)


def _scan_terraform(path: Path, root: Path) -> list[InfraFinding]:
    findings: list[InfraFinding] = []
    rel = str(path.relative_to(root))
    content = path.read_text(errors="replace")
    for match in _TF_PROVIDER_RE.finditer(content):
        provider = match.group(1).lower()
        vendor, jurisdiction, exposure = _classify_tf_provider(provider)
        findings.append(
            InfraFinding(
                file=rel,
                component=f"terraform_provider_{provider}",
                vendor=vendor,
                jurisdiction=jurisdiction,
                cloud_act_exposure=exposure,
                detail=f'provider "{provider}"',
            )
        )
    return findings


def _classify_tf_provider(provider: str) -> tuple[str, str, bool]:
    mapping = {
        "aws":      ("Amazon AWS",       "US", True),
        "azurerm":  ("Microsoft Azure",  "US", True),
        "azuread":  ("Microsoft Azure",  "US", True),
        "google":   ("Google Cloud",     "US", True),
        "gcp":      ("Google Cloud",     "US", True),
        "alicloud": ("Alibaba Cloud",    "CN", False),
        "hetzner":  ("Hetzner",          "EU", False),
        "scaleway": ("Scaleway",         "EU", False),
        "ovh":      ("OVHcloud",         "EU", False),
        "ionos":    ("IONOS Cloud",      "EU", False),
        "stackit":  ("STACKIT",          "EU", False),
        "openstack":("OpenStack",        "Neutral", False),
    }
    return mapping.get(provider, ("Unknown", "Unknown", False))


def _looks_like_k8s(path: Path) -> bool:
    try:
        head = path.read_text(errors="replace")[:2000]
    except OSError:
        return False
    return ("apiVersion:" in head) and ("kind:" in head)


def _scan_k8s(path: Path, root: Path) -> list[InfraFinding]:
    findings: list[InfraFinding] = []
    rel = str(path.relative_to(root))
    content = path.read_text(errors="replace")
    for match in _K8S_STORAGE_CLASS_RE.finditer(content):
        storage_class = match.group(1).lower()
        if any(c in storage_class for c in ("gp2", "gp3", "ebs", "efs")):
            findings.append(
                InfraFinding(
                    file=rel,
                    component="kubernetes_storage_class",
                    vendor="Amazon AWS",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    detail=f"storageClassName: {storage_class}",
                )
            )
        elif "azuredisk" in storage_class or "azurefile" in storage_class:
            findings.append(
                InfraFinding(
                    file=rel,
                    component="kubernetes_storage_class",
                    vendor="Microsoft Azure",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    detail=f"storageClassName: {storage_class}",
                )
            )
        elif "pd-standard" in storage_class or "pd-ssd" in storage_class:
            findings.append(
                InfraFinding(
                    file=rel,
                    component="kubernetes_storage_class",
                    vendor="Google Cloud",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    detail=f"storageClassName: {storage_class}",
                )
            )
    return findings


def _scan_env_file(path: Path, root: Path) -> list[InfraFinding]:
    """Flag cloud-endpoint keys without ever printing their values."""
    findings: list[InfraFinding] = []
    rel = str(path.relative_to(root))
    patterns = {
        "AWS_":              ("Amazon AWS",      "US", True),
        "AZURE_":            ("Microsoft Azure", "US", True),
        "GOOGLE_":           ("Google Cloud",    "US", True),
        "GCP_":              ("Google Cloud",    "US", True),
        "OPENAI_":           ("OpenAI",          "US", True),
        "ANTHROPIC_":        ("Anthropic PBC",   "US", True),
    }
    for line in path.read_text(errors="replace").splitlines():
        key = line.split("=", 1)[0].strip()
        for prefix, (vendor, jur, exposure) in patterns.items():
            if key.startswith(prefix):
                findings.append(
                    InfraFinding(
                        file=rel,
                        component="env_var_prefix",
                        vendor=vendor,
                        jurisdiction=jur,
                        cloud_act_exposure=exposure,
                        detail=f"env key: {key}",  # key only, never value
                    )
                )
                break
    return findings
