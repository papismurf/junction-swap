from decimal import Decimal, ROUND_DOWN
import networkx as nx
from typing import List, Optional, Dict, Tuple
from app.models import Pool, SwapRoute, Token
from app.services.token_store import TokenStore


class GraphSolver:
    def __init__(self, token_store: TokenStore):
        self.token_store = token_store
        self.graph = nx.Graph()
        self.pools: Dict[str, Pool] = {}  # Cache pools by address
        self.tokens: Dict[str, Token] = {}  # Cache tokens by address

    async def update_graph(self):
        """Update the graph with current pool data"""
        try:
            # Fetch latest pools and tokens
            pools = await self.token_store.get_all_pools()
            tokens = await self.token_store.get_all_tokens()

            # Update local cache
            self.pools = {pool.address: pool for pool in pools}
            self.tokens = {token.address: token for token in tokens}

            # Clear existing graph
            self.graph.clear()

            # Add nodes (tokens) with their properties
            for token in tokens:
                self.graph.add_node(
                    token.address,
                    symbol=token.symbol,
                    decimals=token.decimals,
                    price_usd=float(token.price_usd or 0)
                )

            # Add edges (pools) with their properties
            for pool in pools:
                # Calculate edge weight based on liquidity and price impact
                weight = self._calculate_edge_weight(pool)

                # Add edge with pool information
                self.graph.add_edge(
                    pool.token0.address,
                    pool.token1.address,
                    weight=weight,
                    pool_address=pool.address,
                    reserve0=float(pool.reserve0),
                    reserve1=float(pool.reserve1)
                )

        except Exception as e:
            print(f"Error updating graph: {str(e)}")

    def _calculate_edge_weight(self, pool: Pool) -> float:
        """
        Calculate edge weight based on pool liquidity and price impact.
        Lower weight means better path.
        """
        try:
            # Get token prices
            price0 = float(pool.token0.price_usd or 0)
            price1 = float(pool.token1.price_usd or 0)

            # Calculate total liquidity in USD
            liquidity_usd = (
                    float(pool.reserve0) * price0 +
                    float(pool.reserve1) * price1
            )

            # Base weight on liquidity (inverse relationship)
            # Higher liquidity = lower weight = preferred path
            if liquidity_usd > 0:
                weight = 1 / (liquidity_usd ** 0.5)

                # Add small constant to avoid zero weights
                return weight + 0.0001
            else:
                return float('inf')

        except Exception as e:
            print(f"Error calculating edge weight: {str(e)}")
            return float('inf')

    async def find_best_route(
            self,
            token_in_address: str,
            token_out_address: str,
            amount_in: Decimal,
            max_hops: int = 3
    ) -> Optional[SwapRoute]:
        """
        Find the best route for swapping between two tokens.

        Args:
            token_in_address: Address of input token
            token_out_address: Address of output token
            amount_in: Input amount
            max_hops: Maximum number of hops in the path

        Returns:
            SwapRoute object if route is found, None otherwise
        """
        try:
            best_route = None
            best_output_amount = Decimal(0)

            # Try paths with increasing number of hops
            for n_hops in range(1, max_hops + 1):
                # Find all simple paths with exactly n_hops hops
                paths = list(nx.all_simple_paths(
                    self.graph,
                    token_in_address,
                    token_out_address,
                    cutoff=n_hops
                ))

                # Evaluate each path
                for path in paths:
                    pools, output_amount = self._get_path_details(path, amount_in)

                    # Update best route if this path gives better output
                    if output_amount > best_output_amount:
                        best_output_amount = output_amount
                        best_route = SwapRoute(
                            path=path,
                            pools=pools,
                            estimated_output=output_amount
                        )

            return best_route

        except Exception as e:
            print(f"Error finding best route: {str(e)}")
            return None

    def _get_path_details(
            self,
            path: List[str],
            amount_in: Decimal
    ) -> Tuple[List[str], Decimal]:
        """
        Calculate the pools to use and output amount for a given path.

        Args:
            path: List of token addresses in the path
            amount_in: Input amount

        Returns:
            Tuple of (pool_addresses, output_amount)
        """
        pools = []
        current_amount = amount_in

        # Process each pair of tokens in the path
        for i in range(len(path) - 1):
            token_in = path[i]
            token_out = path[i + 1]

            # Get pool data from the graph
            edge_data = self.graph.get_edge_data(token_in, token_out)
            if not edge_data:
                return [], Decimal(0)

            pool_address = edge_data['pool_address']
            pools.append(pool_address)

            # Calculate output amount for this hop
            pool = self.pools[pool_address]
            current_amount = self._calculate_output_amount(
                pool,
                token_in,
                token_out,
                current_amount
            )

            # If any hop returns 0, the path is invalid
            if current_amount == Decimal(0):
                return [], Decimal(0)

        return pools, current_amount

    def _calculate_output_amount(
            self,
            pool: Pool,
            token_in_address: str,
            token_out_address: str,
            amount_in: Decimal
    ) -> Decimal:
        """
        Calculate the output amount for a swap in a single pool.

        Args:
            pool: Pool object
            token_in_address: Address of input token
            token_out_address: Address of output token
            amount_in: Input amount

        Returns:
            Expected output amount
        """
        try:
            # Determine if we're going token0 -> token1 or token1 -> token0
            is_token0_to_token1 = token_in_address == pool.token0.address

            # Get reserves in correct order
            reserve_in = pool.reserve0 if is_token0_to_token1 else pool.reserve1
            reserve_out = pool.reserve1 if is_token0_to_token1 else pool.reserve0

            # Constant product formula: k = x * y
            # y_out = y_current - (k / (x_current + x_in))
            k = reserve_in * reserve_out
            new_reserve_in = reserve_in + amount_in

            # Calculate output amount
            if new_reserve_in > 0:
                new_reserve_out = k / new_reserve_in
                output_amount = reserve_out - new_reserve_out

                # Apply a 0.3% fee
                output_amount = output_amount * Decimal('0.997')

                # Round down to token decimals
                token_out = self.tokens[token_out_address]
                return output_amount.quantize(
                    Decimal(f'1e-{token_out.decimals}'),
                    rounding=ROUND_DOWN
                )

            return Decimal(0)

        except Exception as e:
            print(f"Error calculating output amount: {str(e)}")
            return Decimal(0)

    def _validate_reserves(self, pool: Pool) -> bool:
        """Validate pool reserves are sufficient for trading"""
        min_reserve = Decimal('1e-6')
        return pool.reserve0 > min_reserve and pool.reserve1 > min_reserve
