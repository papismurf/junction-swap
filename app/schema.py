from typing import List, Optional
from decimal import Decimal
import strawberry
from strawberry.types import Info
from app.models import Token as TokenModel


@strawberry.type
class Token:
    """GraphQL Token type"""
    address: str
    symbol: str
    name: str
    price_usd: float = strawberry.field(name="priceUsd")
    decimals: int

    @classmethod
    def from_model(cls, token: TokenModel) -> "Token":
        return cls(
            address=token.address,
            symbol=token.symbol,
            name=token.name,
            price_usd=float(token.price_usd if token.price_usd is not None else 0),
            decimals=token.decimals
        )


@strawberry.type
class SwapRoute:
    path: List[str]
    pools: List[str]
    estimated_output: float = strawberry.field(name="estimatedOutput")


@strawberry.type
class Query:
    @strawberry.field
    async def available_tokens(self, info: Info) -> List[Token]:
        try:
            token_store = info.context["token_store"]
            tokens = await token_store.get_all_tokens()
            return [Token.from_model(token) for token in tokens]
        except Exception as e:
            print(f"Error in available_tokens: {str(e)}")
            return []

    @strawberry.field
    async def top_tokens(
            self,
            info: Info,
            limit: int = 100  # Default value set here instead of in argument
    ) -> List[Token]:
        try:
            token_store = info.context["token_store"]
            tokens = await token_store.get_top_tokens(limit)
            return [Token.from_model(token) for token in tokens]
        except Exception as e:
            print(f"Error in top_tokens: {str(e)}")
            return []

    @strawberry.field
    async def best_swap_route(
            self,
            info: Info,
            token_in: str,
            token_out: str,
            amount_in: float
    ) -> Optional[SwapRoute]:
        try:
            graph_solver = info.context["graph_solver"]
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
        except Exception as e:
            print(f"Error in best_swap_route: {str(e)}")
            return None


# Create the schema
schema = strawberry.Schema(query=Query)
