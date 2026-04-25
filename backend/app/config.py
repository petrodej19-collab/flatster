from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/nepremicnine_tracker"

    SCRAPER_HEADLESS: bool = True
    SCRAPER_MAX_DETAIL_PAGES_PER_RUN: int = 100
    SCRAPER_PAGE_DELAY_MIN: float = 2.0
    SCRAPER_PAGE_DELAY_MAX: float = 5.0
    SCRAPER_DETAIL_DELAY_MIN: float = 1.0
    SCRAPER_DETAIL_DELAY_MAX: float = 3.0
    SCRAPER_PAGE_TIMEOUT_MS: int = 30000
    SCRAPER_MAX_RETRIES: int = 3

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Scheduler
    SCHEDULE_INTERVAL_HOURS: float = 6.0

    # Sold detection
    SOLD_DETECTION_MISSES: int = 3

    # AI Scoring
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-haiku-4-5-20251001"
    AI_MAX_LISTINGS_PER_RUN: int = 50
    AI_SCORING_DELAY: float = 0.5

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
