from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="", validation_alias="POSTGRES_PASSWORD")

    qdrant_host: str = Field(default="localhost", validation_alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, validation_alias="QDRANT_PORT")
    qdrant_collection: str = Field(default="", validation_alias="QDRANT_COLLECTION")

    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")

    llm_api_url: str = Field(default="", validation_alias="LLM_API_URL")
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_model: str = Field(default="", validation_alias="LLM_MODEL")
    llm_request_timeout_seconds: float | None = Field(default=None, validation_alias="API_TIMEOUT_SECONDS")

    embedding_model_api_url: str = Field(default="", validation_alias="EMBEDDING_MODEL_API_URL")
    embedding_model_api_key: str = Field(default="", validation_alias="EMBEDDING_MODEL_API_KEY")
    embedding_model: str = Field(default="", validation_alias="EMBEDDING_MODEL")
    embedding_vector_size: int = Field(default=768, validation_alias="EMBEDDING_VECTOR_SIZE")

    mautic_api_url: str = Field(default="", validation_alias="MAUTIC_API_URL")
    mautic_user: str = Field(default="", validation_alias="MAUTIC_USER")
    mautic_password: str = Field(default="", validation_alias="MAUTIC_PASSWORD")

    nats_port: str = Field(default="4222", validation_alias="NATS_PORT")
    nats_monitor_port: str = Field(default="8222", validation_alias="NATS_MONITOR_PORT")
    nats_host: str = Field(default="", validation_alias="NATS_HOST")
    nats_stream_name: str = Field(default="", validation_alias="NATS_STREAM_NAME")

    api_auth_secret: str = Field(default="change-me", validation_alias="API_AUTH_SECRET")
    api_jwt_algorithm: str = Field(default="HS256", validation_alias="API_JWT_ALGORITHM")
    api_jwt_expiration_seconds: int = Field(default=2592000, validation_alias="API_JWT_EXPIRATION_SECONDS")

    api_timeout_seconds: float = Field(default=30.0, validation_alias="API_TIMEOUT_SECONDS")

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    @property
    def llm_api_base_url(self) -> str:
        return self.llm_api_url.strip()

    @property
    def llm_api_bearer_token(self) -> str | None:
        token = self.llm_api_key.strip()
        return token or None

    @property
    def embedding_api_base_url(self) -> str:
        return self.embedding_model_api_url.strip()

    @property
    def embedding_api_bearer_token(self) -> str | None:
        token = self.embedding_model_api_key.strip()
        return token or None

    @property
    def api_base_url(self) -> str:
        return self.llm_api_base_url

    @property
    def api_bearer_token(self) -> str | None:
        return self.llm_api_bearer_token

    @property
    def mautic_api_base_url(self) -> str:
        return self.mautic_api_url.strip()

    @property
    def mautic_api_username(self) -> str | None:
        username = self.mautic_user.strip()
        return username or None

    @property
    def mautic_api_password_value(self) -> str | None:
        password = self.mautic_password.strip()
        return password or None

    @property
    def api_auth_secret_value(self) -> str:
        return self.api_auth_secret.strip()


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
