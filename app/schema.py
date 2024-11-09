from typing import List
import strawberry

from app.models import Token
from app.services.graph_solver import GraphSolver
from app.services.token_store import TokenStore


@strawberry.type
class Query:
    def __init__(self, token_store: TokenStore, graph_solver: GraphSolver):
        self.token_store = token_store
        self.graph_solver = graph_solver

    @strawberry.field
    async def top_tokens(self, limit: int = 100) -> List[Token]:
        """Get top tokens by market cap"""
        tokens = await self.token_store.get_top_tokens(limit)
        return [
            Token(
                address=token.address,
                symbol=token.symbol,
                name=token.name,
                price_usd=float(token.price_usd or 0),
                decimals=token.decimals
            )
            for token in tokens
        ]
