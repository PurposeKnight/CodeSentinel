# CodeSentinel

CodeSentinel is an autonomous multi-agent code review and deployment platform.

This first milestone contains the production-oriented FastAPI backend foundation:

- Clean Architecture-inspired package layout
- Environment-based configuration
- Structured logging
- PostgreSQL and Redis connectivity wiring
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

Run backend tests locally:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".\backend[dev]"
.\.venv\Scripts\python -m pytest .\backend
.\.venv\Scripts\python -m ruff check .\backend
```

## Architecture Direction

See [docs/architecture.md](docs/architecture.md) for the planned service boundaries and folder structure.
