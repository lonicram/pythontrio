"""Application configuration settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "PythonTrio"
    debug: bool = False
    database_url: str = "sqlite:///./pythontrio.db"

    class Config:
        env_file = ".env"


settings = Settings()
