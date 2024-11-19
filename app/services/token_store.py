import json
import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
import redis.asyncio as redis
from app.models import Token, Pool
from app.config import settings

logger = logging.getLogger(__name__)


class TokenStore:
    def __init__(self):
        """Initialize TokenStore without connecting to Redis"""
        self.redis: Optional[redis.Redis] = None
        self._ready = asyncio.Event()
        self._tokens_cache: Dict[str, Token] = {}
        self._pools_cache: Dict[str, Pool] = {}

    async def wait_ready(self):
        """Wait for Redis to be ready"""
        await self._ready.wait()

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            logger.info("Initializing Redis connection")
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await self.redis.ping()
            self._ready.set()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Error initializing Redis connection: {str(e)}")
            raise

    async def _ensure_connection(self):
        """Ensure Redis connection is established"""
        if not self._ready.is_set():
            await self.initialize()
        if self.redis is None:
            raise Exception("Redis connection not initialized")

    async def save_token(self, token: Token) -> bool:
        """Save a token to Redis and update cache"""
        await self._ensure_connection()
        try:
            token_data = {
                "address": token.address.lower(),
                "symbol": token.symbol,
                "name": token.name,
                "decimals": token.decimals,
                "price_usd": str(token.price_usd) if token.price_usd else None
            }

            # Save to Redis
            await self.redis.hset(
                "tokens",
                token.address.lower(),
                json.dumps(token_data)
            )

            # Update cache
            self._tokens_cache[token.address.lower()] = token
            return True
        except Exception as e:
            logger.error(f"Error saving token {token.address}: {str(e)}")
            return False

    async def save_pool(self, pool: Pool) -> bool:
        """Save a pool to Redis and update cache"""
        await self._ensure_connection()
        try:
            pool_data = {
                "address": pool.address.lower(),
                "token0": {
                    "address": pool.token0.address.lower(),
                    "symbol": pool.token0.symbol,
                    "name": pool.token0.name,
                    "decimals": pool.token0.decimals,
                    "price_usd": str(pool.token0.price_usd) if pool.token0.price_usd else None
                },
                "token1": {
                    "address": pool.token1.address.lower(),
                    "symbol": pool.token1.symbol,
                    "name": pool.token1.name,
                    "decimals": pool.token1.decimals,
                    "price_usd": str(pool.token1.price_usd) if pool.token1.price_usd else None
                },
                "reserve0": str(pool.reserve0),
                "reserve1": str(pool.reserve1)
            }

            # Save to Redis
            await self.redis.hset(
                "pools",
                pool.address.lower(),
                json.dumps(pool_data)
            )

            # Update cache
            self._pools_cache[pool.address.lower()] = pool
            return True
        except Exception as e:
            logger.error(f"Error saving pool {pool.address}: {str(e)}")
            return False

    async def get_token(self, address: str) -> Optional[Token]:
        """Get a token by address"""
        address = address.lower()

        # Check cache first
        if address in self._tokens_cache:
            return self._tokens_cache[address]

        await self._ensure_connection()
        try:
            token_data = await self.redis.hget("tokens", address)
            if not token_data:
                return None

            data = json.loads(token_data)
            token = Token(
                address=data["address"],
                symbol=data["symbol"],
                name=data["name"],
                decimals=data["decimals"],
                price_usd=Decimal(data["price_usd"]) if data["price_usd"] else None
            )

            # Update cache
            self._tokens_cache[address] = token
            return token
        except Exception as e:
            logger.error(f"Error getting token {address}: {str(e)}")
            return None

    async def get_all_tokens(self) -> List[Token]:
        """Get all tokens from Redis and update cache"""
        await self._ensure_connection()
        try:
            tokens_data = await self.redis.hgetall("tokens")
            tokens: List[Token] = []

            for token_data in tokens_data.values():
                try:
                    data = json.loads(token_data)
                    token = Token(
                        address=data["address"],
                        symbol=data["symbol"],
                        name=data["name"],
                        decimals=data["decimals"],
                        price_usd=Decimal(data["price_usd"]) if data["price_usd"] else None
                    )
                    tokens.append(token)
                    # Update cache
                    self._tokens_cache[token.address.lower()] = token
                except Exception as e:
                    logger.error(f"Error parsing token data: {str(e)}")
                    continue

            return tokens
        except Exception as e:
            logger.error(f"Error getting all tokens: {str(e)}")
            return []

    async def get_all_pools(self) -> List[Pool]:
        """Get all pools from Redis and update cache"""
        await self._ensure_connection()
        try:
            pools_data = await self.redis.hgetall("pools")
            pools: List[Pool] = []

            for pool_data in pools_data.values():
                try:
                    data = json.loads(pool_data)

                    token0 = Token(
                        address=data["token0"]["address"],
                        symbol=data["token0"]["symbol"],
                        name=data["token0"]["name"],
                        decimals=data["token0"]["decimals"],
                        price_usd=Decimal(data["token0"]["price_usd"]) if data["token0"]["price_usd"] else None
                    )

                    token1 = Token(
                        address=data["token1"]["address"],
                        symbol=data["token1"]["symbol"],
                        name=data["token1"]["name"],
                        decimals=data["token1"]["decimals"],
                        price_usd=Decimal(data["token1"]["price_usd"]) if data["token1"]["price_usd"] else None
                    )

                    pool = Pool(
                        address=data["address"],
                        token0=token0,
                        token1=token1,
                        reserve0=Decimal(data["reserve0"]),
                        reserve1=Decimal(data["reserve1"])
                    )
                    pools.append(pool)
                    # Update cache
                    self._pools_cache[pool.address.lower()] = pool
                except Exception as e:
                    logger.error(f"Error parsing pool data: {str(e)}")
                    continue

            return pools
        except Exception as e:
            logger.error(f"Error getting all pools: {str(e)}")
            return []

    async def get_top_tokens(self, limit: int = 100) -> List[Token]:
        """Get top tokens sorted by price"""
        try:
            tokens = await self.get_all_tokens()

            # Sort by price_usd
            sorted_tokens = sorted(
                tokens,
                key=lambda x: float(x.price_usd if x.price_usd else 0),
                reverse=True
            )

            return sorted_tokens[:limit]
        except Exception as e:
            logger.error(f"Error getting top tokens: {str(e)}")
            return []

    async def clear_all(self):
        """Clear all data from Redis and cache"""
        await self._ensure_connection()
        try:
            await self.redis.delete("tokens", "pools")
            self._tokens_cache.clear()
            self._pools_cache.clear()
            logger.info("Cleared all data from Redis and cache")
        except Exception as e:
            logger.error(f"Error clearing data: {str(e)}")
