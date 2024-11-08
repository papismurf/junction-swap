from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    GECKOTERMINAL_API_URL: str = "https://api.geckoterminal.com/api/v2"
    REDIS_URL: str = "redis://localhost:6379"
    CHAIN_ID: str = "bsc"  # Binance Smart Chain as example
    UPDATE_INTERVAL: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
