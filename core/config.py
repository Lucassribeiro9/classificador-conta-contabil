from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Carrega o token de admin a partir da variável de ambiente
class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/classificador.db")
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore"  # Ignora variáveis de ambiente extras
    )
settings = Settings()