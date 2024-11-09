import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
import strawberry
from app.schema import Query
from app.services.token_store import TokenStore
from app.services.asset_loader import AssetLoader
from app.services.graph_solver import GraphSolver

# Initialize services
token_store = TokenStore()
asset_loader = AssetLoader(token_store)
graph_solver = GraphSolver(token_store)

# Track background tasks
background_tasks = set()


async def update_graph_periodic():
    """Periodic task to update the graph"""
    while True:
        await graph_solver.update_graph()
        await asyncio.sleep(60)  # Update every minute


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Create background tasks
    try:
        # Start asset loader update task
        loader_task = asyncio.create_task(asset_loader.start_updating())
        background_tasks.add(loader_task)
        loader_task.add_done_callback(background_tasks.discard)

        # Start graph update task
        graph_task = asyncio.create_task(update_graph_periodic())
        background_tasks.add(graph_task)
        graph_task.add_done_callback(background_tasks.discard)

        print("Background tasks started successfully")
        yield
    finally:
        # Shutdown: Cancel all running background tasks
        print("Shutting down background tasks...")
        for task in background_tasks:
            task.cancel()

        # Wait for all tasks to complete
        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
        print("All background tasks shut down")


# Create GraphQL schema
schema = strawberry.Schema(query=Query)

# Create FastAPI app with lifespan handler
app = FastAPI(lifespan=lifespan)

# Add GraphQL route
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
