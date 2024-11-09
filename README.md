# Swap Service

A Python-based swap service that finds optimal routes for token swaps using GeckoTerminal data. The service implements a GraphQL API for querying available tokens and finding the best swap routes.

## Features

- 🔄 Real-time pool and token data updates from GeckoTerminal
- 📊 Optimal route finding using graph-based algorithms
- ⚡ High-performance async operations
- 🗄️ Redis-based caching for fast data access
- 📈 Support for multi-hop swaps
- 🔍 Advanced price impact calculations
- 🎯 GraphQL API for easy integration

## Prerequisites

- Python 3.8+
- Redis
- Docker (optional, for Redis)

## Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd junction_swap
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start Redis:
```bash
# Using Docker
docker run -d -p 6379:6379 redis

# Or use your existing Redis instance
```

5. Create a `.env` file:
```env
GECKOTERMINAL_API_URL=https://api.geckoterminal.com/api/v2
REDIS_URL=redis://localhost:6379
CHAIN_ID=bsc
UPDATE_INTERVAL=300
```

## Running the Application

Start the application using uvicorn:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Usage

### GraphQL Endpoint

The GraphQL endpoint is available at `http://localhost:8000/graphql`.

### Available Queries

1. Get all available tokens:
```graphql
query {
  availableTokens {
    address
    symbol
    name
    priceUsd
  }
}
```

2. Get top tokens by market cap:
```graphql
query {
  topTokens(limit: 50) {
    address
    symbol
    name
    priceUsd
  }
}
```

3. Find best swap route:
```graphql
query {
  bestSwapRoute(
    tokenIn: "0x...",
    tokenOut: "0x...",
    amountIn: 1.0
  ) {
    path
    pools
    estimatedOutput
  }
}
```

## Project Structure

```
swap_service/
├── requirements.txt
├── main.py
├── app/
│   ├── __init__.py
│   ├── schema.py        # GraphQL schema definitions
│   ├── models.py        # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── asset_loader.py    # GeckoTerminal data fetching
│   │   ├── graph_solver.py    # Route finding logic
│   │   └── token_store.py     # Redis storage operations
│   └── config.py       # Configuration settings
```

## Key Components

1. **Asset Loader**
   - Fetches pool and token data from GeckoTerminal
   - Updates data periodically
   - Handles rate limiting and error recovery

2. **Graph Solver**
   - Finds optimal swap routes
   - Implements constant product formula
   - Handles multi-hop routes
   - Calculates price impact

3. **Token Store**
   - Redis-based storage
   - Caches token and pool data
   - Provides fast data access

## Configuration Options

Edit `.env` file to configure:

- `GECKOTERMINAL_API_URL`: GeckoTerminal API endpoint
- `REDIS_URL`: Redis connection URL
- `CHAIN_ID`: Blockchain network identifier (e.g., 'bsc', 'ethereum')
- `UPDATE_INTERVAL`: Data update interval in seconds

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
ruff format
```

## Performance Considerations

- Uses async operations for concurrent processing
- Implements efficient caching with Redis
- Optimizes graph operations for route finding
- Handles background updates efficiently

## Error Handling

The application includes comprehensive error handling:
- API request failures
- Data parsing errors
- Graph calculation errors
- Background task management

## Monitoring

Monitor the application using logs:
- Background task status
- Data update cycles
- Route calculation performance
- Error rates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT License](LICENSE)
