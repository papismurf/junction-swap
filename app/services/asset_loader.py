import asyncio
import httpx
import logging
from typing import List, Dict, Optional
from decimal import Decimal
from app.models import Token, Pool
from app.services.token_store import TokenStore
from app.config import settings

logger = logging.getLogger(__name__)


class AssetLoader:
    def __init__(self, token_store: TokenStore):
        self.token_store = token_store
        self.client = httpx.AsyncClient(
            base_url=settings.GECKOTERMINAL_API_URL,
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "User-Agent": "SwapService/1.0"
            }
        )

    async def fetch_top_tokens(self, limit: int = 100) -> List[Token]:
        """Fetch top tokens from GeckoTerminal"""
        try:
            logger.info(f"Fetching top tokens from GeckoTerminal for network {settings.CHAIN_ID}")

            # Updated endpoint URL
            url = f"/networks/{settings.CHAIN_ID}/pools"
            logger.debug(f"Making request to: {url}")

            response = await self.client.get(
                url,
                params={
                    "page": "1",
                    "limit": str(limit),
                    "sort": "h24_volume_usd_desc,"
                }
            )
            response.raise_for_status()
            data = response.json()

            # Log the raw response
            logger.debug(f"Raw API response: {data}")

            if not data.get("data"):
                logger.warning(f"No data received from API. Response: {data}")
                return []

            tokens_dict: Dict[str, Token] = {}

            for pool_data in data.get("data", []):
                try:
                    attributes = pool_data.get("attributes", {})
                    logger.debug(f"Processing pool attributes: {attributes}")

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
                    logger.error(f"Error processing pool tokens: {str(e)}", exc_info=True)
                    continue

            tokens = list(tokens_dict.values())
            logger.info(f"Found {len(tokens)} unique tokens")

            # Save tokens to store
            for token in tokens:
                success = await self.token_store.save_token(token)
                if not success:
                    logger.warning(f"Failed to save token: {token.symbol} ({token.address})")

            return tokens

        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error fetching top tokens: {str(e)}\nResponse: {e.response.text if hasattr(e, 'response') else 'No response'}")
            return []
        except Exception as e:
            logger.error(f"Error fetching top tokens: {str(e)}", exc_info=True)
            return []

    async def fetch_pools(self) -> List[Pool]:
        """Fetch top pools from GeckoTerminal"""
        try:
            url = f"/networks/{settings.CHAIN_ID}/pools"
            logger.debug(f"Fetching pools from: {url}")

            response = await self.client.get(
                url,
                params={
                    "page": "1",
                    "limit": "100",
                    "sort": "h24_volume_usd_desc"
                }
            )
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Pools API response: {data}")

            if not data.get("data"):
                logger.warning("No pool data received from API")
                return []

            pools = []
            for pool_data in data.get("data", []):
                try:
                    pool = await self._parse_pool_data(pool_data)
                    if pool:
                        await self.token_store.save_pool(pool)
                        pools.append(pool)
                        logger.info(f"Processed pool: {pool.address}")
                except Exception as e:
                    logger.error(f"Error parsing pool data: {str(e)}", exc_info=True)
                    continue

            logger.info(f"Successfully processed {len(pools)} pools")
            return pools

        except httpx.HTTPError as e:
            logger.error(
                f"HTTP error fetching pools: {str(e)}\nResponse: {e.response.text if hasattr(e, 'response') else 'No response'}")
            return []
        except Exception as e:
            logger.error(f"Error fetching pools: {str(e)}", exc_info=True)
            return []

    async def _parse_pool_data(self, data: dict) -> Optional[Pool]:
        """Parse pool data from API response"""
        try:
            attributes = data.get("attributes", {})
            logger.debug(f"Parsing pool attributes: {attributes}")

            # Extract token data
            token0_data = attributes.get("token0", {})
            token1_data = attributes.get("token1", {})

            if not token0_data or not token1_data:
                logger.warning("Missing token data in pool")
                return None

            token0 = Token(
                address=token0_data.get("address", "").lower(),
                symbol=token0_data.get("symbol", ""),
                name=token0_data.get("name", ""),
                decimals=int(token0_data.get("decimals", 18)),
                price_usd=Decimal(str(token0_data.get("price_usd", 0)))
            )

            token1 = Token(
                address=token1_data.get("address", "").lower(),
                symbol=token1_data.get("symbol", ""),
                name=token1_data.get("name", ""),
                decimals=int(token1_data.get("decimals", 18)),
                price_usd=Decimal(str(token1_data.get("price_usd", 0)))
            )

            pool = Pool(
                address=attributes.get("address", "").lower(),
                token0=token0,
                token1=token1,
                reserve0=Decimal(str(attributes.get("reserve0", 0))),
                reserve1=Decimal(str(attributes.get("reserve1", 0)))
            )

            return pool

        except Exception as e:
            logger.error(f"Error parsing pool data: {str(e)}", exc_info=True)
            return None

    async def start_updating(self):
        """Start background updates for both tokens and pools"""
        logger.info("Starting background updates")
        await self.token_store.wait_ready()

        while True:
            try:
                logger.info("Starting update cycle")

                # Fetch both tokens and pools
                tokens = await self.fetch_top_tokens()
                pools = await self.fetch_pools()

                logger.info(f"Update cycle completed. Processed {len(tokens)} tokens and {len(pools)} pools")
            except Exception as e:
                logger.error(f"Error in update cycle: {str(e)}", exc_info=True)

            await asyncio.sleep(settings.UPDATE_INTERVAL)

