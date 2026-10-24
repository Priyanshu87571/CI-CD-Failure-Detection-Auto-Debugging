import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    APP_NAME: str = "DeployGuard"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # Security & JWT
    SECRET_KEY: str = "deployguard-super-secret-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    # Defaults to SQLite async for local development
    DATABASE_URL: str = "sqlite+aiosqlite:///./deployguard.db"
    DB_ECHO: bool = False

    # Redis & Task Worker
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_ASYNC_MEMORY_WORKER: bool = True

    # AI Configuration
    # Supported: "mock", "fallback", "openai", "anthropic", "gemini", "ollama"
    AI_PROVIDER: str = "fallback"
    AI_MODEL: str = "gpt-4o-mini"
    AI_API_KEY: str = ""
    AI_TEMPERATURE: float = 0.2
    AI_MAX_TOKENS: int = 2000
    AI_TIMEOUT_SECONDS: int = 30

    # GitHub App & Webhooks
    GITHUB_TOKEN: str = ""
    GITHUB_APP_ID: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_APP_PRIVATE_KEY_PATH: str = ""

    # Verification Sandbox
    # Options: "isolated_process", "docker"
    VERIFICATION_RUNNER_TYPE: str = "isolated_process"
    VERIFICATION_TIMEOUT_SECONDS: int = 45

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["*"]


settings = Settings()
