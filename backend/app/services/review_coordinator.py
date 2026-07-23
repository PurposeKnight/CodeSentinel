import uuid
from app.core.logging import get_logger
from app.domain.models import AgentTask, PullRequestReview
from app.domain.ports import EventPublisher, NotificationPublisher, ReviewRepository, SlackPublisher

logger = get_logger(__name__)


class ReviewCoordinator:
    def __init__(
        self,
        repository: ReviewRepository,
        notifier: NotificationPublisher,
        slack_publisher: SlackPublisher | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._notifier = notifier
        self._slack_publisher = slack_publisher
        self._event_publisher = event_publisher

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

        # Retrieve repository settings
        repo_settings = await self._repository.get_repository_settings(review.repository)
        min_security = 70
        min_overall = 60
        slack_webhook = None
        enabled_agents = ["security-agent", "code-review-agent", "testing-agent", "documentation-agent", "deployment-agent"]
        if isinstance(repo_settings, dict):
            min_security = repo_settings.get("min_security_score", 70)
            min_overall = repo_settings.get("min_overall_score", 60)
            slack_webhook = repo_settings.get("slack_webhook_url")
            enabled_agents = repo_settings.get("enabled_agents", enabled_agents)

        deployment_enabled = "deployment-agent" in enabled_agents

        # Separate deployment task from analysis tasks
        analysis_tasks = [t for t in tasks if t.agent != "deployment-agent"]
        deployment_task = next((t for t in tasks if t.agent == "deployment-agent"), None)

        analysis_finished = all(t.status in {"completed", "failed"} for t in analysis_tasks)
        if not analysis_finished:
            logger.info(
                "review_coordinator_analysis_tasks_pending",
                review_id=review_id,
                total=len(analysis_tasks),
                pending=len([t for t in analysis_tasks if t.status not in {"completed", "failed"}]),
            )
            return

        # If deployment-agent is enabled
        if deployment_enabled:
            # If analysis tasks are finished, but deployment task hasn't been created yet
            if not deployment_task:
                logger.info("review_coordinator_evaluating_deployment_gates", review_id=review_id)

                overall_score = review.calculate_overall_score()
                security_score = review.security_score

                passed = True
                reason = "All deployment gates passed successfully."

                if security_score is not None and security_score < min_security:
                    passed = False
                    reason = f"Deployment gated: security score ({security_score}) is below the threshold of {min_security}."
                elif overall_score is not None and overall_score < min_overall:
                    passed = False
                    reason = f"Deployment gated: overall quality score ({overall_score}) is below the threshold of {min_overall}."

                task_id = str(uuid.uuid4())
                if not passed:
                    logger.warning("review_coordinator_deployment_gated", review_id=review_id, reason=reason)
                    new_task = AgentTask(
                        id=task_id,
                        review_id=review_id,
                        agent="deployment-agent",
                        status="failed",
                        reason=reason,
                        report={"status": "gated", "reason": reason},
                    )
                    await self._repository.save_task(new_task)
                    tasks = await self._repository.get_tasks(review_id)
                    deployment_task = new_task
                else:
                    logger.info("review_coordinator_deployment_passed_gates", review_id=review_id)
                    new_task = AgentTask(
                        id=task_id,
                        review_id=review_id,
                        agent="deployment-agent",
                        status="pending",
                        reason="Gates passed. Deployment in progress.",
                    )
                    await self._repository.save_task(new_task)

                    if self._event_publisher:
                        await self._event_publisher.publish_agent_task(
                            review_id=review_id,
                            task_id=task_id,
                            agent="deployment-agent",
                            repository=review.repository,
                            pull_request_number=review.pull_request_number,
                        )
                    else:
                        logger.warning(
                            "review_coordinator_event_publisher_missing_cannot_trigger_deployment",
                            review_id=review_id,
                        )
                    return

            # If deployment task exists but is not finished yet
            if deployment_task and deployment_task.status not in {"completed", "failed"}:
                logger.info("review_coordinator_waiting_for_deployment", review_id=review_id)
                return
        else:
            logger.info("review_coordinator_deployment_disabled_skipping_gate", review_id=review_id)

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

        # If deployment task failed, the review fails
        if deployment_enabled:
            deployment_success = deployment_task and deployment_task.status == "completed"
        else:
            deployment_success = any(t.status == "completed" for t in analysis_tasks)

        new_status = "completed" if deployment_success else "failed"

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
                webhook_url=slack_webhook,
            )

        logger.info("review_coordinator_finalized_and_notified", review_id=review_id)
