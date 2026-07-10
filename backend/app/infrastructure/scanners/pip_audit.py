import asyncio
import json
import pathlib
from typing import Any

from app.core.logging import get_logger
from app.infrastructure.scanners.base import Scanner

logger = get_logger(__name__)


class PipAuditScanner(Scanner):
    async def scan(self, target_dir: str) -> list[dict[str, Any]]:
        logger.info("pip_audit_scan_starting", target_dir=target_dir)

        # Check if project has Python dependency files
        path = pathlib.Path(target_dir)
        has_dep_file = any(
            (path / file).exists()
            for file in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]
        )
        if not has_dep_file:
            logger.info("pip_audit_skip_no_dependency_files")
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                "pip-audit",
                "--format",
                "json",
                cwd=target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
        except FileNotFoundError:
            logger.warning("pip_audit_binary_not_found")
            return []

        findings = []
        try:
            output_str = stdout.decode("utf-8").strip()
            if not output_str:
                return findings

            data = json.loads(output_str)
            dependencies = data.get("dependencies", [])
            for dep in dependencies:
                vulns = dep.get("vulns", [])
                for vuln in vulns:
                    findings.append(
                        {
                            "scanner": "pip-audit",
                            "vulnerability_id": vuln.get("id", "unknown"),
                            "file": "requirements.txt",
                            "line": None,
                            "severity": "high",
                            "description": (
                                f"Dependency {dep.get('name')} ({dep.get('version')}) "
                                f"has vulnerability: {vuln.get('description', '')}. "
                                f"Fix: {vuln.get('fix_version', 'N/A')}"
                            ),
                            "code_snippet": None,
                        }
                    )
        except Exception as exc:
            logger.warning("pip_audit_parse_failed", error=str(exc))

        logger.info("pip_audit_scan_completed", findings_count=len(findings))
        return findings
