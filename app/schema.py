from typing import List, Optional
from decimal import Decimal
import strawberry
from app.models import Token as TokenModel


@strawberry.type
class Token:
    """GraphQL Token type"""
    address: str
    symbol: str
    name: str
    price_usd: float
    decimals: int

    @classmethod
    def from_model(cls, token: TokenModel) -> "Token":
        """Convert from Pydantic model to Strawberry type"""
        return cls(
            address=token.address,
            symbol=token.symbol,
            name=token.name,
            price_usd=float(token.price_usd if token.price_usd is not None else 0),
            decimals=token.decimals
        )


@strawberry.type
class SwapRoute:
    """GraphQL SwapRoute type"""
    path: List[str]
    pools: List[str]
    estimated_output: float


@strawberry.type
class Query:
    @strawberry.field
    async def top_tokens(
            self,
            info: strawberry.types.Info,
            limit: int = strawberry.argument(description="Number of tokens to return")
    ) -> List[Token]:
        """Get top tokens by market cap"""

        # Use a default value if limit is None
        actual_limit = limit if limit is not None else 100

        # Get token_store from context
        token_store = info.context["token_store"]

        # Fetch tokens from store
        tokens = await token_store.get_top_tokens(actual_limit)
        return [Token.from_model(token) for token in tokens]

    @strawberry.field
    async def best_swap_route(
            self,
            info: strawberry.types.Info,
            token_in: str = strawberry.argument(description="Input token address"),
            token_out: str = strawberry.argument(description="Output token address"),
            amount_in: float = strawberry.argument(description="Input amount"),
    ) -> Optional[SwapRoute]:
        """Find the best route for swapping between two tokens"""
        # Get graph_solver from context
        graph_solver = info.context["graph_solver"]

        # Find best route
        route = await graph_solver.find_best_route(
            token_in_address=token_in,
            token_out_address=token_out,
            amount_in=Decimal(str(amount_in))
        )

        if route:
            return SwapRoute(
                path=route.path,
                pools=route.pools,
                estimated_output=float(route.estimated_output)
            )
        return None


# Create the schema
schema = strawberry.Schema(query=Query)
