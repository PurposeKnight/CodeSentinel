import tempfile
from typing import Any

from app.core.logging import get_logger
from app.domain.ports import CodeReviewer
from app.infrastructure.git_service import GitService

logger = get_logger(__name__)


class CodeReviewAgentService:
    def __init__(self, git_service: GitService, reviewer: CodeReviewer) -> None:
        self._git_service = git_service
        self._reviewer = reviewer

    async def run_code_review(self, repository: str, pr_number: int) -> dict[str, Any]:
        logger.info("code_review_analysis_starting", repository=repository, pr_number=pr_number)

        with tempfile.TemporaryDirectory(prefix="codesentinel_review_") as tmp_dir:
            # 1. Clone and check out the target PR branch
            await self._git_service.clone_and_checkout_pr(
                repository=repository,
                pr_number=pr_number,
                target_dir=tmp_dir,
            )

            # 2. Get git diff
            diff = await self._git_service.get_diff(tmp_dir)

            # 3. Call code reviewer LLM
            logger.info("code_review_running_llm_reviewer")
            report = await self._reviewer.review_code(diff)

            logger.info(
                "code_review_analysis_completed",
                architecture_score=report.get("architecture_score"),
                performance_score=report.get("performance_score"),
                findings_count=len(report.get("findings", [])),
            )
            return report
