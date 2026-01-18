from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Environment variables are the source of truth.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FastAPI + Kafka + Postgres + Socket.IO Demo"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_incoming: str = "demo.events.incoming"
    kafka_consumer_group: str = "demo.consumer"
    create_topics: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/app"


settings = Settings()
