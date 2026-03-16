from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://shiftmanager:shiftmanager@localhost:5432/shiftmanager"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Business rules
    MIN_REST_HOURS: int = 11
    MAX_CONSECUTIVE_DAYS: int = 6
    MAX_NIGHT_SHIFTS_PER_MONTH: int = 8

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Convert Railway's postgresql:// to postgresql+asyncpg:// if needed."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
