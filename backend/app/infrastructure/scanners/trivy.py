import asyncio
import json
import pathlib
from typing import Any

from app.core.logging import get_logger
from app.infrastructure.scanners.base import Scanner

logger = get_logger(__name__)


class TrivyScanner(Scanner):
    async def scan(self, target_dir: str) -> list[dict[str, Any]]:
        logger.info("trivy_scan_starting", target_dir=target_dir)
        report_file = pathlib.Path(target_dir) / "trivy_report.json"

        report_file.unlink(missing_ok=True)

        try:
            proc = await asyncio.create_subprocess_exec(
                "trivy",
                "fs",
                "--format",
                "json",
                "--output",
                report_file.name,
                ".",
                cwd=target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except FileNotFoundError:
            logger.warning("trivy_binary_not_found")
            return []

        findings = []
        if report_file.exists():
            try:
                with report_file.open("r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        results = data.get("Results", [])
                        for result in results:
                            target = result.get("Target", "")

                            # 1. Parse CVEs / vulnerabilities
                            vulns = result.get("Vulnerabilities", [])
                            for vuln in vulns:
                                pkg_name = vuln.get("PkgName", "unknown")
                                inst_ver = vuln.get("InstalledVersion", "unknown")
                                fix_ver = vuln.get("FixedVersion", "N/A")
                                desc = vuln.get("Description", "")
                                desc_str = f"Pkg: {pkg_name} ({inst_ver}). Fix: {fix_ver}. {desc}"

                                findings.append(
                                    {
                                        "scanner": "trivy",
                                        "vulnerability_id": vuln.get("VulnerabilityID", "unknown"),
                                        "file": target,
                                        "line": None,
                                        "severity": vuln.get("Severity", "low").lower(),
                                        "description": desc_str,
                                        "code_snippet": None,
                                    }
                                )

                            # 2. Parse infrastructure misconfigurations
                            misconfigs = result.get("Misconfigurations", [])
                            for mis in misconfigs:
                                findings.append(
                                    {
                                        "scanner": "trivy",
                                        "vulnerability_id": mis.get("ID", "unknown"),
                                        "file": target,
                                        "line": None,
                                        "severity": mis.get("Severity", "low").lower(),
                                        "description": f"{mis.get('Title')}: {mis.get('Message')}",
                                        "code_snippet": None,
                                    }
                                )
                report_file.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("trivy_parse_failed", error=str(exc))

        logger.info("trivy_scan_completed", findings_count=len(findings))
        return findings
