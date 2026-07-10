import asyncio
import json
from typing import Any

from app.core.logging import get_logger
from app.infrastructure.scanners.base import Scanner

logger = get_logger(__name__)


class SemgrepScanner(Scanner):
    async def scan(self, target_dir: str) -> list[dict[str, Any]]:
        logger.info("semgrep_scan_starting", target_dir=target_dir)
        try:
            proc = await asyncio.create_subprocess_exec(
                "semgrep",
                "scan",
                "--config=auto",
                "--json",
                cwd=target_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
        except FileNotFoundError:
            logger.warning("semgrep_binary_not_found")
            return []

        findings = []
        try:
            output_str = stdout.decode("utf-8").strip()
            if not output_str:
                return findings

            data = json.loads(output_str)
            results = data.get("results", [])
            for result in results:
                extra = result.get("extra", {})
                metadata = extra.get("metadata", {})

                raw_severity = (
                    metadata.get("severity")
                    or extra.get("severity")
                    or "WARNING"
                ).upper()
                severity = "medium"
                if raw_severity == "ERROR":
                    severity = "high"
                elif raw_severity == "INFO":
                    severity = "info"

                findings.append(
                    {
                        "scanner": "semgrep",
                        "vulnerability_id": result.get("check_id", "unknown"),
                        "file": result.get("path", ""),
                        "line": result.get("start", {}).get("line"),
                        "severity": severity,
                        "description": extra.get("message", ""),
                        "code_snippet": extra.get("lines", ""),
                    }
                )
        except Exception as exc:
            logger.warning("semgrep_parse_failed", error=str(exc))

        logger.info("semgrep_scan_completed", findings_count=len(findings))
        return findings
