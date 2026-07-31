from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agent.graph import build_graph
from app.api.v1.router import api_router
from app.config import settings


from app.services.price_bus import start_finnhub, stop_finnhub

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
        import subprocess
        from pathlib import Path
        
        backend_dir = Path(__file__).parent.parent
        print("Running database migrations...")
        # Run alembic relative to the backend directory, so it works on Render
        subprocess.run(["alembic", "upgrade", "head"], cwd=str(backend_dir), shell=True)
        
        await checkpointer.setup()  # creates checkpoint tables on first run, no-op after
        app.state.graph = build_graph(checkpointer)
        
        
        await start_finnhub(app)
        try:
            yield
        finally:
            await stop_finnhub()


app = FastAPI(title="FinSight API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")