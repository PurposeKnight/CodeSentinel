# CodeSentinel

CodeSentinel is an autonomous multi-agent code review and deployment platform.

This first milestone contains the production-oriented FastAPI backend foundation:

- Clean Architecture-inspired package layout
- Environment-based configuration
- Structured logging
- PostgreSQL and Redis connectivity wiring
- PostgreSQL repository persistence for PR reviews and agent tasks
- RabbitMQ event publishing for verified GitHub webhooks
- RabbitMQ downstream agent task queues (`codesentinel.tasks.security`, etc.)
- Planner Worker consumption for pull request workflow planning, persistence, and task routing
- Docker and Docker Compose support
- Health and readiness endpoints
- GitHub webhook placeholder endpoint

## Backend Quick Start

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Start the local stack:

```powershell
docker compose up --build
```

The API will be available at:

```text
http://localhost:8000
```

Useful endpoints:

- `GET /health`
- `GET /health/ready`
- `POST /api/v1/webhooks/github`

GitHub webhook requests must include `X-Hub-Signature-256`, signed with `GITHUB_WEBHOOK_SECRET`.
Verified webhook events are published to RabbitMQ. The Planner Worker consumes those events, creates a pull request review record in PostgreSQL, creates associated agent task records in status `pending`, and publishes the tasks to RabbitMQ for execution.

Run backend tests locally:

```powershell
python -m venv .venv
cd backend
..\.venv\Scripts\python -m pytest
..\.venv\Scripts\python -m ruff check .
```

## Architecture Direction

See [docs/architecture.md](docs/architecture.md) for the planned service boundaries and folder structure.
