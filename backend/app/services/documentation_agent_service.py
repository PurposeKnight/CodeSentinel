import tempfile
from typing import Any

from app.core.logging import get_logger
from app.domain.ports import DocAnalyzer
from app.infrastructure.git_service import GitService

logger = get_logger(__name__)


class DocumentationAgentService:
    def __init__(self, git_service: GitService, doc_analyzer: DocAnalyzer) -> None:
        self._git_service = git_service
        self._doc_analyzer = doc_analyzer

    async def run_documentation_analysis(self, repository: str, pr_number: int) -> dict[str, Any]:
        logger.info("documentation_analysis_starting", repository=repository, pr_number=pr_number)

        with tempfile.TemporaryDirectory(prefix="codesentinel_doc_") as tmp_dir:
            # 1. Clone and check out the target PR branch
            await self._git_service.clone_and_checkout_pr(
                repository=repository,
                pr_number=pr_number,
                target_dir=tmp_dir,
            )

            # 2. Call doc analyzer
            logger.info("documentation_running_llm_analyzer")
            report = await self._doc_analyzer.analyze_documentation(tmp_dir)

            logger.info(
                "documentation_analysis_completed",
                documentation_score=report.get("documentation_score"),
                findings_count=len(report.get("findings", [])),
            )
            return report
