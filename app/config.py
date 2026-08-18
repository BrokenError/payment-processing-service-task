from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str
    database_url: str
    rabbitmq_url: str
    log_level: str = "INFO"

    outbox_poll_interval_seconds: float = 1.0
    outbox_batch_size: int = 50

    payment_process_min_seconds: float = 2.0
    payment_process_max_seconds: float = 5.0
    payment_success_rate: float = 0.9

    webhook_timeout_seconds: float = 10.0
    consumer_max_attempts: int = 3


settings = Settings()
