"""
sentinel.scanner.infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Scan infrastructure-as-code and deployment config for sovereign
posture. We read files as text, we do not execute them.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Directories we never enumerate — pruned at walk time, not after yield,
# so scanning a home-dir-sized tree never crawls ~/Library, ~/node_modules,
# or a gigabyte-scale .venv.
_EXCLUDED_DIRS = frozenset(
    {
        ".venv",
        "venv",
        ".git",
        "node_modules",
        ".tox",
        "dist",
        "build",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }
)

# Hard cap on directory depth. Prevents unbounded walks if the scanner is
# accidentally pointed at a large directory (e.g. the user's home dir).
_DEFAULT_MAX_DEPTH = 3

# Default wall-clock budget for a single scan. None = unlimited (tests).
# This is a belt-and-suspenders guarantee on top of walk-time pruning so
# scan() can never block the caller indefinitely, even if a future bug
# or a pathological symlink graph defeats the depth limit. The check is
# a monotonic-clock comparison inside the walk loop — fully reentrant,
# thread-safe, signal-free, and cross-platform.
_DEFAULT_TIMEOUT_SECONDS: float = 5.0


class _Deadline:
    """Cooperative deadline checker. Reentrant, signal-free."""

    __slots__ = ("_expires_at",)

    def __init__(self, timeout_seconds: float | None) -> None:
        self._expires_at: float | None = (
            time.monotonic() + timeout_seconds if timeout_seconds is not None else None
        )

    def expired(self) -> bool:
        if self._expires_at is None:
            return False
        return time.monotonic() >= self._expires_at


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
    max_depth_scanned: int = _DEFAULT_MAX_DEPTH
    timed_out: bool = False

    @property
    def us_controlled_components(self) -> int:
        return sum(1 for f in self.findings if f.jurisdiction == "US")

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_scanned": self.files_scanned,
            "total_findings": len(self.findings),
            "us_controlled_components": self.us_controlled_components,
            "max_depth_scanned": self.max_depth_scanned,
            "timed_out": self.timed_out,
            "scan_note": (
                f"Scanned up to {self.max_depth_scanned} directory levels "
                "deep from repo_root. Excluded dirs (.venv, node_modules, "
                ".git, etc.) are pruned at walk time."
                + (" Scan deadline reached — partial results." if self.timed_out else "")
            ),
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

    def scan(
        self,
        repo_root: str | Path = ".",
        *,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        timeout_seconds: float | None = _DEFAULT_TIMEOUT_SECONDS,
    ) -> InfraScanResult:
        """Scan IaC files under ``repo_root``.

        The walk is pruned at traversal time: it never descends into
        excluded directories (``.venv``, ``node_modules``, ``.git`` …)
        and never goes deeper than ``max_depth`` levels. This bounds
        scan cost even when ``repo_root`` is accidentally pointed at a
        large tree like the user's home directory.

        ``timeout_seconds`` is a cooperative wall-clock budget. When
        exceeded the scan stops at the next file boundary and returns
        the partial result with ``timed_out=True``. The check is a
        monotonic-clock comparison — no signals, fully reentrant,
        thread-safe, works on every platform.
        """
        root = Path(repo_root)
        deadline = _Deadline(timeout_seconds)
        result = InfraScanResult(max_depth_scanned=max_depth)

        # Phase 1: terraform
        for tf in sorted(_walk_files(root, ("*.tf", "*.tfvars"), max_depth, deadline)):
            if deadline.expired():
                break
            result.files_scanned += 1
            for finding in _scan_terraform(tf, root):
                result.findings.append(finding)
        if deadline.expired():
            result.timed_out = True
            return result

        # Phase 2: kubernetes manifests
        for yaml_path in sorted(_walk_files(root, ("*.yaml", "*.yml"), max_depth, deadline)):
            if deadline.expired():
                break
            if not _looks_like_k8s(yaml_path):
                continue
            result.files_scanned += 1
            for finding in _scan_k8s(yaml_path, root):
                result.findings.append(finding)
        if deadline.expired():
            result.timed_out = True
            return result

        # Phase 3: repo-root .env
        env_path = root / ".env"
        if env_path.exists():
            result.files_scanned += 1
            for finding in _scan_env_file(env_path, root):
                result.findings.append(finding)
        if deadline.expired():
            result.timed_out = True

        return result


def _walk_files(
    root: Path,
    patterns: tuple[str, ...],
    max_depth: int = _DEFAULT_MAX_DEPTH,
    deadline: _Deadline | None = None,
) -> Iterator[Path]:
    """Yield files under ``root`` matching any glob in ``patterns``.

    Uses :func:`os.walk` with in-place ``dirs`` pruning so excluded
    directories and directories past ``max_depth`` are never entered.
    Symlinks are not followed. If ``deadline`` is supplied, iteration
    stops as soon as the deadline has elapsed (cooperative cancel).
    """
    root_resolved = root.resolve(strict=False)
    if not root_resolved.exists():
        return
    root_str = str(root_resolved)

    for current, dirs, files in os.walk(root_str, followlinks=False):
        if deadline is not None and deadline.expired():
            return

        rel = os.path.relpath(current, root_str)
        depth = 0 if rel == "." else rel.count(os.sep) + 1

        # Prune excluded directories in-place so walk never descends
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
        # Stop descending past max_depth
        if depth >= max_depth:
            dirs[:] = []

        for fname in files:
            for pattern in patterns:
                if fnmatch.fnmatch(fname, pattern):
                    yield Path(current) / fname
                    break


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
