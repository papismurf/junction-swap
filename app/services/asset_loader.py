import asyncio
import httpx
from typing import List
from decimal import Decimal
from app.models import Token, Pool
from app.services.token_store import TokenStore
from app.config import settings


class AssetLoader:
    def __init__(self, token_store: TokenStore):
        self.token_store = token_store
        self.client = httpx.AsyncClient(
            base_url=settings.GECKOTERMINAL_API_URL,
            timeout=30.0
        )

    async def fetch_top_tokens(self, limit: int = 100) -> List[Token]:
        """
        Fetch top tokens by market cap from GeckoTerminal.

        Args:
            limit: Number of tokens to fetch (default: 100)

        Returns:
            List[Token]: List of top tokens
        """
        try:
            # Fetch tokens from GeckoTerminal
            response = await self.client.get(
                f"/networks/{settings.CHAIN_ID}/tokens",
                params={
                    "page": 1,
                    "limit": limit,
                    "sort": "market_cap"
                }
            )
            response.raise_for_status()
            data = response.json()

            tokens = []
            for token_data in data.get("data", []):
                attributes = token_data.get("attributes", {})

                # Extract token data
                token = Token(
                    address=attributes.get("address", "").lower(),
                    symbol=attributes.get("symbol", ""),
                    name=attributes.get("name", ""),
                    decimals=int(attributes.get("decimals", 18)),
                    price_usd=Decimal(str(attributes.get("price_usd", 0)))
                )

                # Save token to store
                await self.token_store.save_token(token)
                tokens.append(token)

            return tokens

        except httpx.HTTPError as e:
            print(f"Error fetching top tokens: {str(e)}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching top tokens: {str(e)}")
            return []

    async def fetch_pools(self) -> List[Pool]:
        """Fetch top pools from GeckoTerminal"""
        try:
            response = await self.client.get(
                f"/networks/{settings.CHAIN_ID}/pools",
                params={
                    "page": 1,
                    "limit": 100,
                    "sort": "liquidity"
                }
            )
            response.raise_for_status()
            data = response.json()

            pools = []
            for pool_data in data.get("data", []):
                try:
                    pool = await self._parse_pool_data(pool_data)
                    if pool:
                        await self.token_store.save_pool(pool)
                        await self.token_store.save_token(pool.token0)
                        await self.token_store.save_token(pool.token1)
                        pools.append(pool)
                except Exception as e:
                    print(f"Error parsing pool data: {str(e)}")
                    continue

            return pools

        except httpx.HTTPError as e:
            print(f"Error fetching pools: {str(e)}")
            return []
        except Exception as e:
            print(f"Unexpected error fetching pools: {str(e)}")
            return []

    async def _parse_pool_data(self, data: dict) -> Pool:
        """Parse pool data from API response"""
        try:
            attributes = data.get("attributes", {})

            # Extract token data
            token0_data = attributes.get("token0", {})
            token1_data = attributes.get("token1", {})

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

            return Pool(
                address=attributes.get("address", "").lower(),
                token0=token0,
                token1=token1,
                reserve0=Decimal(str(attributes.get("reserve0", 0))),
                reserve1=Decimal(str(attributes.get("reserve1", 0)))
            )

        except Exception as e:
            print(f"Error parsing pool data: {str(e)}")
            return None

    async def start_updating(self):
        """Start background updates for both tokens and pools"""
        # Wait for TokenStore to be ready
        await self.token_store.wait_ready()

        while True:
            try:
                # Fetch top tokens and pools concurrently
                await asyncio.gather(
                    self.fetch_top_tokens(),
                    self.fetch_pools()
                )
            except Exception as e:
                print(f"Error in update cycle: {str(e)}")

            await asyncio.sleep(settings.UPDATE_INTERVAL)
