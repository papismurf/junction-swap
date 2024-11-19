import asyncio
import httpx
import logging
from typing import List, Dict
from decimal import Decimal
from app.models import Token, Pool
from app.services.token_store import TokenStore
from app.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssetLoader:
    def __init__(self, token_store: TokenStore):
        self.token_store = token_store
        self.client = httpx.AsyncClient(
            base_url=settings.GECKOTERMINAL_API_URL,
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "User-Agent": "JunctionSwap/1.0"
            }
        )

    async def fetch_top_tokens(self, limit: int = 100) -> List[Token]:
        """Fetch top tokens from GeckoTerminal"""
        try:
            logger.info(f"Fetching top tokens from GeckoTerminal for network {settings.CHAIN_ID}")

            # First, get the network details to ensure it's valid
            response = await self.client.get(
                f"/networks/{settings.CHAIN_ID}/pools/"
            )
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Received data from API: {data}")

            tokens_dict: Dict[str, Token] = {}

            for pool_data in data.get("data", []):
                try:
                    attributes = pool_data.get("attributes", {})

                    # Process token0
                    token0_data = attributes.get("token0", {})
                    if token0_data:
                        address = token0_data.get("address", "").lower()
                        if address and address not in tokens_dict:
                            token = Token(
                                address=address,
                                symbol=token0_data.get("symbol", ""),
                                name=token0_data.get("name", ""),
                                decimals=int(token0_data.get("decimals", 18)),
                                price_usd=Decimal(str(token0_data.get("price_usd", 0)))
                            )
                            tokens_dict[address] = token
                            logger.info(f"Processed token0: {token.symbol} ({token.address})")

                    # Process token1
                    token1_data = attributes.get("token1", {})
                    if token1_data:
                        address = token1_data.get("address", "").lower()
                        if address and address not in tokens_dict:
                            token = Token(
                                address=address,
                                symbol=token1_data.get("symbol", ""),
                                name=token1_data.get("name", ""),
                                decimals=int(token1_data.get("decimals", 18)),
                                price_usd=Decimal(str(token1_data.get("price_usd", 0)))
                            )
                            tokens_dict[address] = token
                            logger.info(f"Processed token1: {token.symbol} ({token.address})")

                except Exception as e:
                    logger.error(f"Error processing pool tokens: {str(e)}")
                    continue

            tokens = list(tokens_dict.values())

            # Save tokens to store
            for token in tokens:
                success = await self.token_store.save_token(token)
                if not success:
                    logger.warning(f"Failed to save token: {token.symbol} ({token.address})")

            logger.info(f"Successfully processed {len(tokens)} tokens")
            return tokens

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching top tokens: {str(e)}\nFor more information check: {e.request.url}")
            return []
        except Exception as e:
            logger.error(f"Error fetching top tokens: {str(e)}")
            return []

    async def fetch_pools(self) -> List[Pool]:
        """Fetch top pools from GeckoTerminal"""
        try:
            response = await self.client.get(
                f"/networks/{settings.CHAIN_ID}/pools/"
            )
            response.raise_for_status()
            data = response.json()

            pools = []
            for pool_data in data.get("data", []):
                try:
                    pool = await self._parse_pool_data(pool_data)
                    if pool:
                        await self.token_store.save_pool(pool)
                        pools.append(pool)
                        logger.info(f"Processed pool: {pool.address}")
                except Exception as e:
                    logger.error(f"Error parsing pool data: {str(e)}")
                    continue

            logger.info(f"Successfully processed {len(pools)} pools")
            return pools

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching pools: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching pools: {str(e)}")
            return []

    async def start_updating(self):
        """Start background updates for both tokens and pools"""
        logger.info("Starting background updates")
        await self.token_store.wait_ready()

        while True:
            try:
                logger.info("Starting update cycle")
                tokens = await self.fetch_top_tokens()
                logger.info(f"Update cycle completed. Processed {len(tokens)} tokens")
            except Exception as e:
                logger.error(f"Error in update cycle: {str(e)}")

            await asyncio.sleep(settings.UPDATE_INTERVAL)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
