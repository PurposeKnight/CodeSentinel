import tempfile
from typing import Any

from app.core.logging import get_logger
from app.domain.ports import TestAnalyzer
from app.infrastructure.git_service import GitService

logger = get_logger(__name__)


class TestingAgentService:
    __test__ = False

    def __init__(self, git_service: GitService, test_analyzer: TestAnalyzer) -> None:
        self._git_service = git_service
        self._test_analyzer = test_analyzer

    async def run_testing_analysis(self, repository: str, pr_number: int) -> dict[str, Any]:
        logger.info("testing_analysis_starting", repository=repository, pr_number=pr_number)

        with tempfile.TemporaryDirectory(prefix="codesentinel_testing_") as tmp_dir:
            # 1. Clone and check out the target PR branch
            await self._git_service.clone_and_checkout_pr(
                repository=repository,
                pr_number=pr_number,
                target_dir=tmp_dir,
            )

            # 2. Call test analyzer
            logger.info("testing_running_llm_analyzer")
            report = await self._test_analyzer.analyze_tests(tmp_dir)

            logger.info(
                "testing_analysis_completed",
                findings_count=len(report.get("findings", [])),
            )
            return report
