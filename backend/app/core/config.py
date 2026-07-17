from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CodeSentinel API"
    app_env: str = "local"
    app_debug: bool = False
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "codesentinel"
    postgres_user: str = "codesentinel"
    postgres_password: SecretStr = Field(default=SecretStr("codesentinel"))

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr | None = None

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "codesentinel"
    rabbitmq_password: SecretStr = Field(default=SecretStr("codesentinel"))
    rabbitmq_vhost: str = "/"
    rabbitmq_exchange: str = "codesentinel.events"
    rabbitmq_github_webhook_queue: str = "codesentinel.github.webhooks"
    rabbitmq_github_webhook_routing_key: str = "github.webhook.received"
    rabbitmq_connect_retries: int = 10
    rabbitmq_connect_retry_delay_seconds: float = 2.0
    planner_worker_prefetch_count: int = 5

    github_webhook_secret: SecretStr = Field(default=SecretStr("change-me"))

    openai_api_key: SecretStr = Field(default=SecretStr("mock-key"))
    openai_api_base: str | None = None
    openai_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def postgres_dsn(self) -> str:
        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        password = self.redis_password.get_secret_value() if self.redis_password else None
        auth = f":{password}@" if password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def rabbitmq_url(self) -> str:
        password = self.rabbitmq_password.get_secret_value()
        vhost = "%2F" if self.rabbitmq_vhost == "/" else self.rabbitmq_vhost
        return (
            f"amqp://{self.rabbitmq_user}:{password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{vhost}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
