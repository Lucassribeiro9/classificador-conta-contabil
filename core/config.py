from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/classificador.db")

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore"  # Ignora variáveis de ambiente extras
    )
settings = Settings()