from app.domain.events import GitHubWebhookEvent, PlannedAgentTask, PullRequestReviewPlan


class PlannerService:
    def plan_github_webhook(self, event: GitHubWebhookEvent) -> PullRequestReviewPlan | None:
        if event.event != "pull_request":
            return None

        if event.action not in {"opened", "reopened", "synchronize", "ready_for_review"}:
            return None

        if not event.repository_full_name:
            return None

        return PullRequestReviewPlan(
            delivery_id=event.delivery_id,
            repository_full_name=event.repository_full_name,
            pull_request_number=self._pull_request_number(event),
            action=event.action,
            tasks=(
                PlannedAgentTask(
                    agent="security-agent",
                    reason="Run Semgrep, Trivy, Gitleaks, Bandit, and dependency audit.",
                ),
                PlannedAgentTask(
                    agent="code-review-agent",
                    reason="Review maintainability, architecture, readability, and duplication.",
                ),
                PlannedAgentTask(
                    agent="testing-agent",
                    reason="Detect missing tests and suggest unit and integration coverage.",
                ),
                PlannedAgentTask(
                    agent="documentation-agent",
                    reason="Assess docs, docstrings, API documentation, and changelog impact.",
                ),
            ),
        )

    @staticmethod
    def _pull_request_number(event: GitHubWebhookEvent) -> int | None:
        pull_request = event.payload.get("pull_request")
        if not isinstance(pull_request, dict):
            return None

        number = pull_request.get("number")
        return number if isinstance(number, int) else None
