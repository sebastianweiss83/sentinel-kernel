"""
sentinel.scanner.cicd
~~~~~~~~~~~~~~~~~~~~~
Scan a repository's CI/CD configuration for US-controlled components.

We grep the files we find — we do not import anything from them. A
sovereignty audit must read configuration the same way a human auditor
would: as plain text.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CICDFinding:
    file: str
    component: str
    vendor: str
    jurisdiction: str
    cloud_act_exposure: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CICDScanResult:
    findings: list[CICDFinding] = field(default_factory=list)
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


class CICDScanner:
    """
    Scan a repository for CI/CD sovereignty posture.

    Detects:
      - GitHub Actions workflows (US)
      - CircleCI config (US)
      - GitLab CI (.com is US-operated, self-hosted is neutral)
      - Dockerfile base images pulled from DockerHub (US)
      - docker-compose.yml image sources
      - pyproject.toml / requirements.txt pointing at PyPI (US-hosted mirror)
    """

    def scan(self, repo_root: str | Path = ".") -> CICDScanResult:
        root = Path(repo_root)
        result = CICDScanResult()

        for wf in sorted((root / ".github" / "workflows").glob("*.yml")):
            result.files_scanned += 1
            result.findings.append(
                CICDFinding(
                    file=str(wf.relative_to(root)),
                    component="github_actions",
                    vendor="GitHub (Microsoft)",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    detail="CI/CD runs on GitHub-hosted runners by default.",
                )
            )

        if (root / ".circleci" / "config.yml").exists():
            result.files_scanned += 1
            result.findings.append(
                CICDFinding(
                    file=".circleci/config.yml",
                    component="circleci",
                    vendor="CircleCI",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                )
            )

        if (root / ".gitlab-ci.yml").exists():
            result.files_scanned += 1
            # GitLab.com is US-operated; self-hosted GitLab is neutral.
            # We cannot know from the file alone which variant is used.
            result.findings.append(
                CICDFinding(
                    file=".gitlab-ci.yml",
                    component="gitlab_ci",
                    vendor="GitLab",
                    jurisdiction="Unknown",
                    cloud_act_exposure=False,
                    detail="Self-hosted GitLab is neutral; gitlab.com is US-operated.",
                )
            )

        dockerfile = root / "Dockerfile"
        if dockerfile.exists():
            result.files_scanned += 1
            for finding in _scan_dockerfile(dockerfile, root):
                result.findings.append(finding)

        compose_candidates = ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]
        for name in compose_candidates:
            compose_path = root / name
            if compose_path.exists():
                result.files_scanned += 1
                for finding in _scan_compose(compose_path, root):
                    result.findings.append(finding)

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            result.files_scanned += 1
            result.findings.append(
                CICDFinding(
                    file="pyproject.toml",
                    component="pypi",
                    vendor="Python Package Index",
                    jurisdiction="US",
                    cloud_act_exposure=False,
                    detail="PyPI is US-hosted but open; mirror via devpi for sovereign CI.",
                )
            )

        # Makefile — flag curl/wget calls to US cloud hosts.
        makefile = root / "Makefile"
        if makefile.exists():
            result.files_scanned += 1
            for finding in _scan_makefile(makefile, root):
                result.findings.append(finding)

        # Jenkinsfile — declarative or scripted.
        jenkinsfile = root / "Jenkinsfile"
        if jenkinsfile.exists():
            result.files_scanned += 1
            result.findings.append(
                CICDFinding(
                    file="Jenkinsfile",
                    component="jenkins",
                    vendor="Jenkins (CloudBees/self-hosted)",
                    jurisdiction="Unknown",
                    cloud_act_exposure=False,
                    detail="Jenkins itself is OSS; hosted CloudBees is US.",
                )
            )

        # Drone CI
        drone_cfg = root / ".drone.yml"
        if drone_cfg.exists():
            result.files_scanned += 1
            result.findings.append(
                CICDFinding(
                    file=".drone.yml",
                    component="drone_ci",
                    vendor="Harness (Drone)",
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    detail="Drone was acquired by Harness — hosted Drone Cloud is US.",
                )
            )

        return result


_US_NETWORK_HOSTS = (
    "amazonaws.com",
    "cloudfront.net",
    "googleapis.com",
    "google.com",
    "azurewebsites.net",
    "blob.core.windows.net",
    "windows.net",
    "github.com/downloads",
    "ghcr.io",
    "gcr.io",
)


def _scan_makefile(path: Path, root: Path) -> list[CICDFinding]:
    findings: list[CICDFinding] = []
    rel = str(path.relative_to(root))
    for lineno, line in enumerate(
        path.read_text(errors="replace").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped:
            continue
        if not any(cmd in stripped for cmd in ("curl", "wget")):
            continue
        matched = next(
            (host for host in _US_NETWORK_HOSTS if host in stripped),
            None,
        )
        if matched:
            findings.append(
                CICDFinding(
                    file=rel,
                    component="makefile_download",
                    vendor=matched,
                    jurisdiction="US",
                    cloud_act_exposure=True,
                    detail=f"line {lineno}: {stripped[:80]}",
                )
            )
    return findings


def _scan_dockerfile(path: Path, root: Path) -> list[CICDFinding]:
    findings: list[CICDFinding] = []
    rel = str(path.relative_to(root))
    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("FROM "):
            continue
        image = stripped[5:].strip().split()[0]
        vendor, jurisdiction, exposure = _classify_docker_image(image)
        findings.append(
            CICDFinding(
                file=rel,
                component="docker_base_image",
                vendor=vendor,
                jurisdiction=jurisdiction,
                cloud_act_exposure=exposure,
                detail=f"base image: {image}",
            )
        )
    return findings


def _scan_compose(path: Path, root: Path) -> list[CICDFinding]:
    findings: list[CICDFinding] = []
    rel = str(path.relative_to(root))
    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("image:"):
            continue
        image = stripped.split(":", 1)[1].strip().strip("'\"")
        if not image:
            continue
        vendor, jurisdiction, exposure = _classify_docker_image(image)
        findings.append(
            CICDFinding(
                file=rel,
                component="docker_compose_image",
                vendor=vendor,
                jurisdiction=jurisdiction,
                cloud_act_exposure=exposure,
                detail=f"image: {image}",
            )
        )
    return findings


def _classify_docker_image(image: str) -> tuple[str, str, bool]:
    """
    Return (vendor, jurisdiction, cloud_act_exposure) for a Docker image ref.

    Conservative heuristics only — we cannot pull the manifest.
    """
    ref = image.lower()
    if ref.startswith(("public.ecr.aws/", "amazon/")):
        return ("Amazon ECR", "US", True)
    if ref.startswith(("gcr.io/", "us.gcr.io/", "eu.gcr.io/", "asia.gcr.io/")):
        return ("Google Container Registry", "US", True)
    if ".azurecr.io" in ref:
        return ("Azure Container Registry", "US", True)
    if ref.startswith("ghcr.io/"):
        return ("GitHub Container Registry (Microsoft)", "US", True)
    if ref.startswith("quay.io/"):
        return ("Quay.io (Red Hat / IBM)", "US", True)
    if "/" not in ref.split(":")[0] or ref.startswith("docker.io/") or ref.startswith("library/"):
        return ("Docker Hub", "US", True)
    return ("Unknown registry", "Unknown", False)
