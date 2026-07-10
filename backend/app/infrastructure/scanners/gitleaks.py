import asyncio
import json
import pathlib
from typing import Any

from app.core.logging import get_logger
from app.infrastructure.scanners.base import Scanner

logger = get_logger(__name__)


class GitleaksScanner(Scanner):
    async def scan(self, target_dir: str) -> list[dict[str, Any]]:
        logger.info("gitleaks_scan_starting", target_dir=target_dir)
        report_file = pathlib.Path(target_dir) / "gitleaks_report.json"

        report_file.unlink(missing_ok=True)

        try:
            proc = await asyncio.create_subprocess_exec(
                "gitleaks",
                "detect",
                "--source=.",
                f"--report-path={report_file.name}",
                "--no-git",
                cwd=target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except FileNotFoundError:
            logger.warning("gitleaks_binary_not_found")
            return []

        findings = []
        if report_file.exists():
            try:
                with report_file.open("r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        for item in data:
                            findings.append(
                                {
                                    "scanner": "gitleaks",
                                    "vulnerability_id": item.get("RuleID", "leak"),
                                    "file": item.get("File", ""),
                                    "line": item.get("StartLine"),
                                    "severity": "high",
                                    "description": (
                                        f"Found sensitive leak: "
                                        f"{item.get('Description', 'credential')}"
                                    ),
                                    "code_snippet": item.get("Match", ""),
                                }
                            )
                report_file.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("gitleaks_parse_failed", error=str(exc))

        logger.info("gitleaks_scan_completed", findings_count=len(findings))
        return findings
