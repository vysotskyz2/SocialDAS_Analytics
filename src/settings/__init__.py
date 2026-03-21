from pydantic_settings import BaseSettings
from src.settings.db import DatabaseConfig


class Settings(BaseSettings):
    db: DatabaseConfig = DatabaseConfig()


settings = Settings()
