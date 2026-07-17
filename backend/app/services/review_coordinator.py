from app.core.logging import get_logger
from app.domain.models import PullRequestReview
from app.domain.ports import NotificationPublisher, ReviewRepository, SlackPublisher

logger = get_logger(__name__)


class ReviewCoordinator:
    def __init__(
        self,
        repository: ReviewRepository,
        notifier: NotificationPublisher,
        slack_publisher: SlackPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._slack_publisher = slack_publisher

    async def check_and_finalize_review(self, review_id: str) -> None:
        review = await self._repository.get_review(review_id)
        if not review:
            logger.warning("review_coordinator_review_not_found", review_id=review_id)
            return

        if review.status in {"completed", "failed"}:
            logger.info("review_coordinator_already_finalized", review_id=review_id, status=review.status)
            return

        # Retrieve all tasks associated with this review
        tasks = await self._repository.get_tasks(review_id)
        if not tasks:
            return

        # Check if all tasks have run to completion/failure
        all_finished = all(t.status in {"completed", "failed"} for t in tasks)
        if not all_finished:
            logger.info(
                "review_coordinator_tasks_pending",
                review_id=review_id,
                total=len(tasks),
                pending=len([t for t in tasks if t.status not in {"completed", "failed"}]),
            )
            return

        logger.info("review_coordinator_all_tasks_finished", review_id=review_id)

        # Compile findings
        all_findings = []
        for task in tasks:
            if task.status == "completed" and task.report:
                report_findings = task.report.get("findings", [])
                if isinstance(report_findings, list):
                    for finding in report_findings:
                        if isinstance(finding, dict):
                            finding_copy = dict(finding)
                            finding_copy["scanner"] = finding_copy.get("scanner", task.agent)
                            all_findings.append(finding_copy)

        has_completed = any(t.status == "completed" for t in tasks)
        new_status = "completed" if has_completed else "failed"

        # Update final state of review
        overall_score = review.calculate_overall_score()
        updated_review = PullRequestReview(
            id=review.id,
            repository=review.repository,
            pull_request_number=review.pull_request_number,
            delivery_id=review.delivery_id,
            status=new_status,
            score=overall_score,
            security_score=review.security_score,
            performance_score=review.performance_score,
            architecture_score=review.architecture_score,
            documentation_score=review.documentation_score,
        )
        await self._repository.save_review(updated_review)

        review_summary = {
            "score": overall_score,
            "security_score": review.security_score,
            "performance_score": review.performance_score,
            "architecture_score": review.architecture_score,
            "documentation_score": review.documentation_score,
        }

        # Publish review findings to GitHub PR
        await self._notifier.publish_pr_review(
            repository=review.repository,
            pr_number=review.pull_request_number,
            review_summary=review_summary,
            findings=all_findings,
        )

        # Publish Slack notifications if publisher is configured
        if self._slack_publisher:
            await self._slack_publisher.publish_review_alert(
                repository=review.repository,
                pr_number=review.pull_request_number,
                score=overall_score,
                status=new_status,
                findings_count=len(all_findings),
                review_id=review.id,
            )

        logger.info("review_coordinator_finalized_and_notified", review_id=review_id)
