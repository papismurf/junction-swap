import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from app.schema import schema
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
        try:
            await graph_solver.update_graph()
        except Exception as e:
            print(f"Error updating graph: {str(e)}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Initialize TokenStore first
        await token_store.initialize()

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
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise
    finally:
        print("Shutting down background tasks...")
        for task in background_tasks:
            task.cancel()

        if background_tasks:
            await asyncio.gather(*background_tasks, return_exceptions=True)
        print("All background tasks shut down")


# Create context for GraphQL
async def get_context() -> Dict[str, Any]:
    return {
        "token_store": token_store,
        "graph_solver": graph_solver
    }


# Create FastAPI app
app = FastAPI(lifespan=lifespan)

# Add GraphQL route with context
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
)
app.include_router(graphql_app, prefix="/graphql")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
