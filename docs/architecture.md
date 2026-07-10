# CodeSentinel Architecture

## Goal Of This Step

This milestone creates the backend foundation that future services and agents can build on. It deliberately stops before implementing agent workflows, GitHub OAuth, queue workers, scanners, or deployment automation.

## Target System Architecture

CodeSentinel will use a modular microservice architecture:

- Frontend: Next.js dashboard for repositories, pull requests, reports, deployments, monitoring, and settings.
- API Gateway: Public REST boundary, authentication enforcement, request routing, and dashboard-facing APIs.
- Auth Service: GitHub OAuth, sessions, organization membership, and token management.
- GitHub Webhook Service: Receives GitHub events, verifies signatures, normalizes events, and publishes jobs.
- Planner Agent: Coordinates PR review workflows and selects downstream agents.
- Security Agent: Runs Semgrep, Trivy, Gitleaks, Bandit, and pip-audit, then explains findings with an LLM.
- Code Review Agent: Reviews maintainability, architecture, duplication, and readability.
- Testing Agent: Identifies missing tests and proposes generated test coverage.
- Documentation Agent: Generates README, API docs, docstrings, and changelog suggestions.
- Deployment Agent: Gates deployment, triggers CI/CD, verifies health, rolls back failures, and reports status.
- Notification Service: Sends GitHub comments, Slack/email notifications, and dashboard events.

Long-running work flows through RabbitMQ. FastAPI services remain responsive and persist workflow state in PostgreSQL, with Redis used for caching, rate limits, temporary workflow state, and idempotency keys.

## Backend Folder Structure

```text
backend/
  app/
    api/
      dependencies/        FastAPI dependency providers
      routes/              HTTP route modules
    core/                  Config, logging, application lifecycle
    domain/                Enterprise business objects and interfaces
    infrastructure/        Database, Redis, queues, external clients
    schemas/               Pydantic request/response models
    services/              Application use cases
    main.py                FastAPI application factory
  tests/
    unit/
    integration/
  Dockerfile
  pyproject.toml
```

## Clean Architecture Direction

The dependency rule is:

```text
api -> services -> domain
infrastructure -> domain interfaces
```

HTTP routes should be thin. They validate transport details and call application services. Services own use-case orchestration. Infrastructure implements external dependencies such as PostgreSQL, Redis, GitHub, OpenAI-compatible LLM providers, RabbitMQ, and scanner runners.

## Current Endpoints

- `GET /health`: Liveness endpoint for process-level health.
- `GET /health/ready`: Readiness endpoint that checks PostgreSQL and Redis connectivity.
- `POST /api/v1/webhooks/github`: Verifies GitHub webhook signatures and publishes accepted events to RabbitMQ for future workflow processing.

## Current Worker

- `planner-worker`: Consumes `codesentinel.github.webhooks`, ignores unsupported events, and creates the initial pull request agent plan for supported PR actions.
