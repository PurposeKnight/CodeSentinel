import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.git_service import GitService
from app.infrastructure.scanners.bandit import BanditScanner
from app.infrastructure.scanners.gitleaks import GitleaksScanner
from app.infrastructure.scanners.pip_audit import PipAuditScanner
from app.infrastructure.scanners.semgrep import SemgrepScanner
from app.infrastructure.scanners.trivy import TrivyScanner
from app.services.security_agent_service import SecurityAgentService


@pytest.mark.asyncio
async def test_git_service_clones_and_checks_out() -> None:
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        git_service = GitService()
        await git_service.clone_and_checkout_pr("org/repo", 42, "/tmp/dir")

        assert mock_exec.call_count == 3
        # Verify first call is clone
        assert mock_exec.call_args_list[0][0][1] == "clone"
        assert mock_exec.call_args_list[0][0][2] == "https://github.com/org/repo.git"
        # Verify second call is fetch PR branch
        assert "fetch" in mock_exec.call_args_list[1][0]
        assert "pull/42/head" in mock_exec.call_args_list[1][0]
        # Verify third call is checkout
        assert "checkout" in mock_exec.call_args_list[2][0]
        assert "FETCH_HEAD" in mock_exec.call_args_list[2][0]


@pytest.mark.asyncio
async def test_bandit_scanner_parses_findings() -> None:
    mock_proc = AsyncMock()
    bandit_output = {
        "results": [
            {
                "test_id": "B101",
                "filename": "app.py",
                "line_number": 10,
                "issue_severity": "HIGH",
                "issue_text": "Use of assert detected.",
                "code": "assert x == y",
            }
        ]
    }
    mock_proc.communicate.return_value = (json.dumps(bandit_output).encode("utf-8"), b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        scanner = BanditScanner()
        findings = await scanner.scan("/tmp/dir")

        assert len(findings) == 1
        assert findings[0]["scanner"] == "bandit"
        assert findings[0]["vulnerability_id"] == "B101"
        assert findings[0]["severity"] == "high"
        assert findings[0]["file"] == "app.py"


@pytest.mark.asyncio
async def test_semgrep_scanner_parses_findings() -> None:
    mock_proc = AsyncMock()
    semgrep_output = {
        "results": [
            {
                "check_id": "rules.python.sec",
                "path": "main.py",
                "start": {"line": 15},
                "extra": {
                    "severity": "ERROR",
                    "message": "SQL Injection vulnerability",
                    "lines": "query = f'SELECT * FROM users'",
                },
            }
        ]
    }
    mock_proc.communicate.return_value = (json.dumps(semgrep_output).encode("utf-8"), b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        scanner = SemgrepScanner()
        findings = await scanner.scan("/tmp/dir")

        assert len(findings) == 1
        assert findings[0]["scanner"] == "semgrep"
        assert findings[0]["vulnerability_id"] == "rules.python.sec"
        assert findings[0]["severity"] == "high"
        assert findings[0]["file"] == "main.py"


@pytest.mark.asyncio
async def test_gitleaks_scanner_parses_report() -> None:
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0

    # Mock file existence and content reading
    gitleaks_output = [
        {
            "RuleID": "generic-api-key",
            "File": "config.yaml",
            "StartLine": 5,
            "Description": "Generic API Key detected",
            "Match": "SECRET_KEY = 'change-me'",
        }
    ]

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open") as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = json.dumps(gitleaks_output)
                mock_open.return_value.__enter__.return_value = mock_file

                scanner = GitleaksScanner()
                findings = await scanner.scan("/tmp/dir")

                assert len(findings) == 1
                assert findings[0]["scanner"] == "gitleaks"
                assert findings[0]["vulnerability_id"] == "generic-api-key"
                assert findings[0]["severity"] == "high"
                assert findings[0]["file"] == "config.yaml"


@pytest.mark.asyncio
async def test_trivy_scanner_parses_report() -> None:
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"")
    mock_proc.returncode = 0

    trivy_output = {
        "Results": [
            {
                "Target": "package.json",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2023-1234",
                        "PkgName": "express",
                        "InstalledVersion": "4.17.0",
                        "FixedVersion": "4.18.0",
                        "Severity": "CRITICAL",
                        "Description": "RCE vulnerability",
                    }
                ],
                "Misconfigurations": [
                    {
                        "ID": "AVD-KS-0001",
                        "Title": "Run as non-root",
                        "Message": "Container should run as non-root user",
                        "Severity": "MEDIUM",
                    }
                ],
            }
        ]
    }

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open") as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = json.dumps(trivy_output)
                mock_open.return_value.__enter__.return_value = mock_file

                scanner = TrivyScanner()
                findings = await scanner.scan("/tmp/dir")

                assert len(findings) == 2
                assert findings[0]["scanner"] == "trivy"
                assert findings[0]["vulnerability_id"] == "CVE-2023-1234"
                assert findings[0]["severity"] == "critical"

                assert findings[1]["scanner"] == "trivy"
                assert findings[1]["vulnerability_id"] == "AVD-KS-0001"
                assert findings[1]["severity"] == "medium"


@pytest.mark.asyncio
async def test_pip_audit_scanner_parses_findings() -> None:
    mock_proc = AsyncMock()
    pip_audit_output = {
        "dependencies": [
            {
                "name": "requests",
                "version": "2.28.0",
                "vulns": [
                    {
                        "id": "PYSEC-2023-56",
                        "description": "CVE-2023-32681 bypass vulnerability",
                        "fix_version": "2.31.0",
                    }
                ],
            }
        ]
    }
    mock_proc.communicate.return_value = (json.dumps(pip_audit_output).encode("utf-8"), b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch("pathlib.Path.exists", return_value=True):  # Pretend dependency file exists
            scanner = PipAuditScanner()
            findings = await scanner.scan("/tmp/dir")

            assert len(findings) == 1
            assert findings[0]["scanner"] == "pip-audit"
            assert findings[0]["vulnerability_id"] == "PYSEC-2023-56"
            assert findings[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_security_agent_service_coordinates_flow() -> None:
    mock_git = AsyncMock()
    mock_explainer = AsyncMock()
    mock_explainer.explain_vulnerability.return_value = {
        "explanation": "LLM Explanation",
        "recommendation": "LLM Recommendation",
        "code_fix": "LLM Fix",
    }

    mock_findings = [
        {
            "scanner": "bandit",
            "vulnerability_id": "B101",
            "file": "app.py",
            "line": 10,
            "severity": "high",
            "description": "Assertion used",
            "code_snippet": "assert True",
        }
    ]

    p_bandit = "app.infrastructure.scanners.bandit.BanditScanner.scan"
    p_gitleaks = "app.infrastructure.scanners.gitleaks.GitleaksScanner.scan"
    p_semgrep = "app.infrastructure.scanners.semgrep.SemgrepScanner.scan"
    p_trivy = "app.infrastructure.scanners.trivy.TrivyScanner.scan"
    p_pip = "app.infrastructure.scanners.pip_audit.PipAuditScanner.scan"

    with patch(p_bandit, return_value=mock_findings):
        with patch(p_gitleaks, return_value=[]):
            with patch(p_semgrep, return_value=[]):
                with patch(p_trivy, return_value=[]):
                    with patch(p_pip, return_value=[]):
                        service = SecurityAgentService(mock_git, mock_explainer)
                        report = await service.run_security_analysis("org/repo", 42)

                        assert report["summary"]["total_vulnerabilities"] == 1
                        assert report["summary"]["high"] == 1
                        assert len(report["findings"]) == 1
                        assert report["findings"][0]["explanation"] == "LLM Explanation"
                        assert report["findings"][0]["recommendation"] == "LLM Recommendation"
                        assert report["findings"][0]["code_fix"] == "LLM Fix"
