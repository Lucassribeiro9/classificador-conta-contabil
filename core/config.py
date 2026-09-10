from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pydantic import Field

# Carrega o token de admin a partir da variável de ambiente
class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/classificador.db")
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    SERVICE_CREDENTIAL_SECRET: str = os.getenv("SERVICE_CREDENTIAL_SECRET", "")
    MODEL_DIR: str = os.getenv("MODEL_DIR", "./data/models")

    RAZAO_STORAGE_DIR: str = "./data/razao-temporario"
    RAZAO_UPLOAD_MAX_BYTES: int = Field(default=50_000_000, gt=0)
    RAZAO_STORAGE_MIN_FREE_BYTES: int = Field(default=5_000_000_000, ge=0)
    RAZAO_STORAGE_MIN_FREE_RATIO: float = Field(default=0.15, ge=0, lt=1)
    RAZAO_FAILED_RETENTION_SECONDS: int = Field(default=86400, gt=0)
    RAZAO_IMPORT_BLOCK_SIZE: int = Field(default=1_000, gt=0)
    RAZAO_WORKER_CONCURRENCY: int = Field(default=1, gt=0)
    RAZAO_HEARTBEAT_SECONDS: int = Field(default=30, gt=0)
    RAZAO_LEASE_SECONDS: int = Field(default=600, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore"  # Ignora variáveis de ambiente extras
    )
settings = Settings()
