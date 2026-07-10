import asyncio
import json
from typing import Any

from app.core.logging import get_logger
from app.infrastructure.scanners.base import Scanner

logger = get_logger(__name__)


class BanditScanner(Scanner):
    async def scan(self, target_dir: str) -> list[dict[str, Any]]:
        logger.info("bandit_scan_starting", target_dir=target_dir)
        proc = await asyncio.create_subprocess_exec(
            "bandit",
            "-r",
            ".",
            "-f",
            "json",
            cwd=target_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        findings = []
        try:
            output_str = stdout.decode("utf-8").strip()
            if not output_str:
                return findings

            data = json.loads(output_str)
            results = data.get("results", [])
            for result in results:
                findings.append(
                    {
                        "scanner": "bandit",
                        "vulnerability_id": result.get("test_id", "unknown"),
                        "file": result.get("filename", ""),
                        "line": result.get("line_number"),
                        "severity": result.get("issue_severity", "low").lower(),
                        "description": result.get("issue_text", ""),
                        "code_snippet": result.get("code", ""),
                    }
                )
        except Exception as exc:
            logger.warning("bandit_parse_failed", error=str(exc))

        logger.info("bandit_scan_completed", findings_count=len(findings))
        return findings
