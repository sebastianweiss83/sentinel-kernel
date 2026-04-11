"""
tests/test_scanner.py
~~~~~~~~~~~~~~~~~~~~~
Tests for the runtime, CI/CD, and infrastructure scanners.
"""

from __future__ import annotations

import json
from pathlib import Path

from sentinel.scanner import (
    CICDScanner,
    InfrastructureScanner,
    RuntimeScanner,
)

# ---------------------------------------------------------------------------
# Runtime scanner
# ---------------------------------------------------------------------------


def test_runtime_scanner_detects_boto3() -> None:
    scanner = RuntimeScanner(installed_packages=[("boto3", "1.34.0")])
    result = scanner.scan()
    assert result.total_packages == 1
    pkg = result.packages[0]
    assert pkg.name == "boto3"
    assert pkg.jurisdiction == "US"
    assert pkg.cloud_act_exposure is True
    assert pkg.in_critical_path is True
    assert result.critical_path_violations  # boto3 is flagged


def test_runtime_scanner_detects_google_cloud() -> None:
    scanner = RuntimeScanner(
        installed_packages=[("google-cloud-storage", "2.14.0")]
    )
    result = scanner.scan()
    assert result.packages[0].parent_company == "Alphabet"
    assert result.packages[0].cloud_act_exposure is True


def test_runtime_scanner_marks_critical_path() -> None:
    scanner = RuntimeScanner(
        installed_packages=[
            ("boto3", "1.34.0"),          # critical path, US → violation
            ("pytest", "8.0.0"),          # dev tool, not critical
            ("psycopg2-binary", "2.9.9"), # OPTIONAL extra → not critical
            ("numpy", "1.26.0"),          # neutral, not critical
        ]
    )
    result = scanner.scan()
    violations = result.critical_path_violations
    assert len(violations) == 1
    assert "boto3" in violations[0]


def test_runtime_scanner_reports_unknown_package() -> None:
    scanner = RuntimeScanner(installed_packages=[("something-obscure", "0.1")])
    result = scanner.scan()
    pkg = result.packages[0]
    assert pkg.jurisdiction == "Unknown"
    assert pkg.parent_company == "Unknown"
    assert pkg.cloud_act_exposure is False  # conservative


def test_runtime_scanner_sovereignty_score() -> None:
    scanner = RuntimeScanner(
        installed_packages=[
            ("boto3", "1.0"),     # US
            ("numpy", "1.0"),     # Neutral
            ("langfuse", "2.0"),  # EU
            ("psycopg2", "2.9"),  # Neutral
        ]
    )
    result = scanner.scan()
    # 3 of 4 are sovereign (non-CLOUD-Act)
    assert result.sovereignty_score == 0.75
    assert result.us_owned_packages == 1


def test_runtime_scanner_no_false_positives_on_sentinel_itself() -> None:
    scanner = RuntimeScanner(installed_packages=[("sentinel-kernel", "0.9.0")])
    result = scanner.scan()
    assert result.packages[0].cloud_act_exposure is False
    assert result.critical_path_violations == []


def test_scan_result_json_export() -> None:
    scanner = RuntimeScanner(installed_packages=[("boto3", "1.34.0")])
    result = scanner.scan()
    data = json.loads(result.to_json())
    assert data["total_packages"] == 1
    assert data["us_owned_packages"] == 1
    assert data["packages"][0]["name"] == "boto3"


# ---------------------------------------------------------------------------
# CI/CD scanner
# ---------------------------------------------------------------------------


def test_cicd_scanner_detects_github_actions(tmp_path: Path) -> None:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "ci.yml").write_text("name: CI\non: push\njobs: {}\n")

    result = CICDScanner().scan(tmp_path)
    assert result.files_scanned >= 1
    findings = [f for f in result.findings if f.component == "github_actions"]
    assert len(findings) == 1
    assert findings[0].jurisdiction == "US"
    assert findings[0].cloud_act_exposure is True


def test_cicd_scanner_detects_dockerhub(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.12-slim\n"
        "RUN pip install sentinel-kernel\n"
    )
    result = CICDScanner().scan(tmp_path)
    docker_findings = [f for f in result.findings if f.component == "docker_base_image"]
    assert len(docker_findings) == 1
    assert docker_findings[0].jurisdiction == "US"
    assert "python:3.12-slim" in docker_findings[0].detail


def test_cicd_scanner_detects_compose_image(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n"
        "  web:\n"
        "    image: grafana/grafana:latest\n"
    )
    result = CICDScanner().scan(tmp_path)
    image_findings = [f for f in result.findings if f.component == "docker_compose_image"]
    assert len(image_findings) == 1
    assert "grafana/grafana:latest" in image_findings[0].detail


def test_cicd_scanner_json_export(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    data = json.loads(CICDScanner().scan(tmp_path).to_json())
    assert "findings" in data
    assert data["files_scanned"] >= 1


# ---------------------------------------------------------------------------
# Infrastructure scanner
# ---------------------------------------------------------------------------


def test_infra_scanner_detects_aws_provider(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text(
        'provider "aws" {\n'
        '  region = "eu-central-1"\n'
        "}\n"
    )
    result = InfrastructureScanner().scan(tmp_path)
    aws_findings = [f for f in result.findings if "aws" in f.component]
    assert len(aws_findings) == 1
    assert aws_findings[0].jurisdiction == "US"
    assert aws_findings[0].cloud_act_exposure is True


def test_infra_scanner_detects_hetzner_as_eu(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('provider "hetzner" {}\n')
    result = InfrastructureScanner().scan(tmp_path)
    assert result.findings[0].jurisdiction == "EU"
    assert result.findings[0].cloud_act_exposure is False


def test_infra_scanner_detects_k8s_aws_storage_class(tmp_path: Path) -> None:
    (tmp_path / "pvc.yaml").write_text(
        "apiVersion: v1\n"
        "kind: PersistentVolumeClaim\n"
        "spec:\n"
        "  storageClassName: gp3\n"
    )
    result = InfrastructureScanner().scan(tmp_path)
    k8s_findings = [f for f in result.findings if f.component == "kubernetes_storage_class"]
    assert len(k8s_findings) == 1
    assert k8s_findings[0].vendor == "Amazon AWS"


def test_infra_scanner_env_file_never_prints_values(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "AWS_ACCESS_KEY_ID=AKIA_SECRET_DO_NOT_LEAK\n"
        "OPENAI_API_KEY=sk-super-secret\n"
    )
    result = InfrastructureScanner().scan(tmp_path)
    for finding in result.findings:
        # Value must never appear in any field
        assert "AKIA_SECRET_DO_NOT_LEAK" not in finding.detail
        assert "sk-super-secret" not in finding.detail
    env_findings = [f for f in result.findings if f.component == "env_var_prefix"]
    assert len(env_findings) >= 2


# ---------------------------------------------------------------------------
# Expanded knowledge base + EU alternatives
# ---------------------------------------------------------------------------


def test_runtime_scanner_detects_crewai_and_autogen() -> None:
    scanner = RuntimeScanner(
        installed_packages=[
            ("crewai", "0.1"),
            ("autogen", "0.2"),
            ("haystack-ai", "2.0"),
        ]
    )
    result = scanner.scan()
    by_name = {p.name: p for p in result.packages}
    assert by_name["crewai"].cloud_act_exposure is True
    assert by_name["autogen"].cloud_act_exposure is True
    assert by_name["haystack-ai"].cloud_act_exposure is False
    assert by_name["haystack-ai"].jurisdiction == "EU"


def test_runtime_scanner_sovereign_alternatives() -> None:
    scanner = RuntimeScanner(
        installed_packages=[
            ("openai", "1.0"),
            ("pinecone-client", "3.0"),
            ("numpy", "1.26"),
        ]
    )
    alts = scanner.scan().sovereign_alternatives()
    assert "openai" in alts
    assert "mistralai" in alts["openai"] or "aleph-alpha" in alts["openai"]
    assert "pinecone-client" in alts
    assert "qdrant" in alts["pinecone-client"] or "weaviate" in alts["pinecone-client"]
    assert "numpy" not in alts


def test_suggest_alternative_helper() -> None:
    from sentinel.scanner.knowledge import suggest_alternative

    assert suggest_alternative("openai") is not None
    assert suggest_alternative("OpenAI") is not None
    assert suggest_alternative("numpy") is None
    assert suggest_alternative("nonexistent") is None


# ---------------------------------------------------------------------------
# CI/CD scanner — new file types
# ---------------------------------------------------------------------------


def test_cicd_scanner_detects_makefile_us_download(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text(
        "setup:\n"
        "\tcurl -sSL https://download.docker.com/linux/install.sh | sh\n"
        "\twget https://s3.amazonaws.com/bucket/tool.tar.gz\n"
    )
    result = CICDScanner().scan(tmp_path)
    makefile_findings = [
        f for f in result.findings if f.component == "makefile_download"
    ]
    assert len(makefile_findings) >= 1
    assert any("amazonaws.com" in f.vendor for f in makefile_findings)


def test_cicd_scanner_makefile_without_us_hosts(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text(
        "install:\n"
        "\tpip install -e .\n"
    )
    result = CICDScanner().scan(tmp_path)
    makefile_findings = [
        f for f in result.findings if f.component == "makefile_download"
    ]
    assert makefile_findings == []


def test_cicd_scanner_detects_jenkinsfile(tmp_path: Path) -> None:
    (tmp_path / "Jenkinsfile").write_text(
        "pipeline { agent any; stages { stage('build') { steps { echo 'hi' } } } }\n"
    )
    result = CICDScanner().scan(tmp_path)
    jenkins_findings = [f for f in result.findings if f.component == "jenkins"]
    assert len(jenkins_findings) == 1


def test_cicd_scanner_detects_drone_yml(tmp_path: Path) -> None:
    (tmp_path / ".drone.yml").write_text("kind: pipeline\nname: default\n")
    result = CICDScanner().scan(tmp_path)
    drone_findings = [f for f in result.findings if f.component == "drone_ci"]
    assert len(drone_findings) == 1
    assert drone_findings[0].cloud_act_exposure is True


# ---------------------------------------------------------------------------
# CLI --suggest-alternatives
# ---------------------------------------------------------------------------


def test_cli_scan_suggest_alternatives_text(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    rc = cli.main([
        "scan", "--runtime", "--suggest-alternatives", "--repo", str(tmp_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # header appears whenever there's at least one known US package installed
    if "EU-SOVEREIGN ALTERNATIVES" in out:
        assert "→" in out


def test_cli_scan_suggest_alternatives_json(tmp_path: Path, capsys) -> None:
    from sentinel import cli

    rc = cli.main([
        "scan", "--runtime", "--suggest-alternatives", "--json",
        "--repo", str(tmp_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "eu_alternatives" in data
    assert isinstance(data["eu_alternatives"], dict)
