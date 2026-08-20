from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Carrega o token de admin a partir da variável de ambiente
class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/classificador.db")
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    SERVICE_CREDENTIAL_SECRET: str = os.getenv("SERVICE_CREDENTIAL_SECRET", "")
    MODEL_DIR: str = os.getenv("MODEL_DIR", "./data/models")

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore"  # Ignora variáveis de ambiente extras
    )
settings = Settings()
