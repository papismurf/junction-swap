from typing import List
import redis
from app.models import Token, Pool
from app.config import settings


class TokenStore:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)

    async def save_token(self, token: Token):
        await self.redis_client.hset(
            "tokens",
            token.address,
            token.model_dump_json()
        )

    async def save_pool(self, pool: Pool):
        await self.redis_client.hset(
            "pools",
            pool.address,
            pool.model_dump_json()
        )

    async def get_all_tokens(self) -> List[Token]:
        tokens_data = await self.redis_client.hgetall("tokens")
        return [Token.model_validate_json(token_data) for token_data in tokens_data.values()]

    async def get_all_pools(self) -> List[Pool]:
        pools_data = await self.redis_client.hgetall("pools")
        return [Pool.model_validate_json(pool_data) for pool_data in pools_data.values()]

    async def get_top_tokens(self, limit: int = 100) -> List[Token]:
        """Get top tokens sorted by market cap"""
        tokens = await self.get_all_tokens()
        return sorted(
            tokens,
            key=lambda x: float(x.price_usd or 0),
            reverse=True
        )[:limit]
