from app.domain.events import GitHubWebhookEvent
from app.services.planner_service import PlannerService


def test_planner_creates_pull_request_review_plan() -> None:
    service = PlannerService()
    event = GitHubWebhookEvent(
        event="pull_request",
        delivery_id="delivery-1",
        action="opened",
        repository_full_name="PurposeKnight/CodeSentinel",
        payload={"pull_request": {"number": 42}},
    )

    plan = service.plan_github_webhook(event)

    assert plan is not None
    assert plan.repository_full_name == "PurposeKnight/CodeSentinel"
    assert plan.pull_request_number == 42
    assert [task.agent for task in plan.tasks] == [
        "security-agent",
        "code-review-agent",
        "testing-agent",
        "documentation-agent",
    ]


def test_planner_ignores_unsupported_events() -> None:
    service = PlannerService()
    event = GitHubWebhookEvent(
        event="push",
        delivery_id="delivery-1",
        action=None,
        repository_full_name="PurposeKnight/CodeSentinel",
        payload={},
    )

    assert service.plan_github_webhook(event) is None


def test_planner_ignores_closed_pull_request_events() -> None:
    service = PlannerService()
    event = GitHubWebhookEvent(
        event="pull_request",
        delivery_id="delivery-1",
        action="closed",
        repository_full_name="PurposeKnight/CodeSentinel",
        payload={"pull_request": {"number": 42}},
    )

    assert service.plan_github_webhook(event) is None
