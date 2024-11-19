import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

# Network identifiers for GeckoTerminal API
NETWORK_IDS = {
    'ethereum': 'eth',
    'binance': 'bsc',
    'polygon': 'polygon',
    'avalanche': 'avalanche',
    'fantom': 'fantom',
    'arbitrum': 'arbitrum',
    'optimism': 'optimism'
}

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    GECKOTERMINAL_API_URL: str = "https://api.geckoterminal.com/api/v2"
    REDIS_URL: str = "redis://localhost:6379"
    CHAIN_ID: str = NETWORK_IDS['ethereum']  # Can change to "polygon", etc.
    UPDATE_INTERVAL: int = 300  # 5 minutes
    LOG_LEVEL: str = "INFO"


settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
