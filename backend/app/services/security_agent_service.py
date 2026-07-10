import asyncio
import tempfile
from typing import Any

from app.core.logging import get_logger
from app.domain.ports import VulnerabilityExplainer
from app.infrastructure.git_service import GitService
from app.infrastructure.scanners import (
    BanditScanner,
    GitleaksScanner,
    PipAuditScanner,
    SemgrepScanner,
    TrivyScanner,
)

logger = get_logger(__name__)


class SecurityAgentService:
    def __init__(
        self,
        git_service: GitService,
        explainer: VulnerabilityExplainer,
    ) -> None:
        self._git_service = git_service
        self._explainer = explainer
        self._scanners = [
            BanditScanner(),
            GitleaksScanner(),
            SemgrepScanner(),
            TrivyScanner(),
            PipAuditScanner(),
        ]

    async def run_security_analysis(
        self,
        repository: str,
        pr_number: int,
    ) -> dict[str, Any]:
        logger.info("security_analysis_starting", repository=repository, pr_number=pr_number)

        with tempfile.TemporaryDirectory(prefix="codesentinel_sec_") as tmp_dir:
            # 1. Clone and check out the target PR branch
            await self._git_service.clone_and_checkout_pr(
                repository=repository,
                pr_number=pr_number,
                target_dir=tmp_dir,
            )

            # 2. Run scanners concurrently
            logger.info("security_analysis_running_scanners")
            tasks = [scanner.scan(tmp_dir) for scanner in self._scanners]
            scan_results = await asyncio.gather(*tasks, return_exceptions=True)

            findings: list[dict[str, Any]] = []
            for result in scan_results:
                if isinstance(result, Exception):
                    logger.error("scanner_run_failed", error=str(result))
                else:
                    findings.extend(result)

            # 3. Enrich findings concurrently via LLM Explainer
            logger.info("security_analysis_enriching_findings", raw_count=len(findings))
            enrich_tasks = [self._enrich_finding(finding) for finding in findings]
            enriched_findings = await asyncio.gather(*enrich_tasks)

            # 4. Generate structured report counts
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
            for f in enriched_findings:
                sev = f.get("severity", "low").lower()
                if sev in severity_counts:
                    severity_counts[sev] += 1
                else:
                    severity_counts["low"] += 1

            report = {
                "summary": {
                    "total_vulnerabilities": len(enriched_findings),
                    "critical": severity_counts["critical"],
                    "high": severity_counts["high"],
                    "medium": severity_counts["medium"],
                    "low": severity_counts["low"],
                    "info": severity_counts["info"],
                },
                "findings": enriched_findings,
            }

            logger.info(
                "security_analysis_completed",
                total_findings=len(enriched_findings),
                critical=severity_counts["critical"],
                high=severity_counts["high"],
            )
            return report

    async def _enrich_finding(self, finding: dict[str, Any]) -> dict[str, Any]:
        try:
            explanation_data = await self._explainer.explain_vulnerability(
                scanner=finding["scanner"],
                vulnerability_detail=finding,
            )
            return {
                **finding,
                "explanation": explanation_data.get("explanation", ""),
                "recommendation": explanation_data.get("recommendation", ""),
                "code_fix": explanation_data.get("code_fix"),
            }
        except Exception as exc:
            logger.warning(
                "finding_enrichment_failed",
                vulnerability_id=finding.get("vulnerability_id"),
                error=str(exc),
            )
            return {
                **finding,
                "explanation": f"Failed to enrich finding: {str(exc)}",
                "recommendation": "Review the vulnerability details directly.",
                "code_fix": None,
            }
