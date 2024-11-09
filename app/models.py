from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel

class Token(BaseModel):
    address: str
    symbol: str
    name: str
    decimals: int
    price_usd: Optional[Decimal]

class Pool(BaseModel):
    address: str
    token0: Token
    token1: Token
    reserve0: Decimal
    reserve1: Decimal

class SwapRoute(BaseModel):
    path: List[str]  # Token addresses in the path
    pools: List[str]  # Pool addresses to use
    estimated_output: Decimal