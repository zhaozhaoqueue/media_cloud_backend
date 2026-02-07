from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Media Cloud API"
    app_version: str = "0.1.0"

    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"
    openapi_url: str | None = "/openapi.json"

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/media_cloud"
    storage_backend: str = "local"
    storage_local_root: str = "./storage"
    storage_base_url: str = "http://localhost:8000"
    read_url_ttl_seconds: int = 600
    read_url_signing_secret: str = "dev-read-url-secret"
    upload_token_ttl_seconds: int = 900
    thumb_max_size: int = 512

    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = False
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
