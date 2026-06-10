"""Application configuration settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "PythonTrio"
    debug: bool = False
    database_url: str = "sqlite:///./pythontrio.db"


settings = Settings()
