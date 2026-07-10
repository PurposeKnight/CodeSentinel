FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (git, curl, tar)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Install Gitleaks
RUN curl -sSLo gitleaks.tar.gz https://github.com/gitleaks/gitleaks/releases/download/v8.18.2/gitleaks_8.18.2_linux_x64.tar.gz \
    && tar -xzf gitleaks.tar.gz -C /usr/local/bin gitleaks \
    && rm gitleaks.tar.gz

# Install Trivy
RUN curl -sSLo trivy.tar.gz https://github.com/aquasecurity/trivy/releases/download/v0.72.0/trivy_0.72.0_Linux-64bit.tar.gz \
    && tar -xzf trivy.tar.gz -C /usr/local/bin trivy \
    && rm trivy.tar.gz

# Install Python-based scanners globally (so they are on PATH)
RUN pip install --no-cache-dir bandit semgrep pip-audit

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY app ./app

# Give app user ownership of /app for temporary workspace checkouts
RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

