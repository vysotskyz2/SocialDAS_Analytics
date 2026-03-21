from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='postgres_',
        env_file='.env',
        extra='ignore',
    )

    host: str = "localhost"
    port: int = 5432
    db: str = "postgres"
    user: str = "postgres"
    password: str = "postgres"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
