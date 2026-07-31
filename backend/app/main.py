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
        import subprocess, os
        print("Running cleanup...")
        files_to_delete = [
            r"d:\AI_Analyzer\backend\app\api\v1\portfolio.py",
            r"d:\AI_Analyzer\backend\app\services\portfolio_service.py",
            r"d:\AI_Analyzer\backend\app\models\portfolio.py",
            r"d:\AI_Analyzer\backend\app\schemas\portfolio.py",
            r"d:\AI_Analyzer\backend\app\agent\tools\portfolio.py",
            r"d:\AI_Analyzer\backend\alembic\versions\f1a2b3c4d5e6_add_portfolio_tables.py",
            r"d:\AI_Analyzer\backend\alembic\versions\8279531a7b0d_merge_divergent_heads.py"
        ]
        for f in files_to_delete:
            if os.path.exists(f): os.remove(f)
            
        pycache_dir = r"d:\AI_Analyzer\backend\alembic\versions\__pycache__"
        import shutil
        if os.path.exists(pycache_dir): shutil.rmtree(pycache_dir)
            
        print("Running database migrations...")
        subprocess.run(["alembic", "upgrade", "head"], cwd="d:\\AI_Analyzer\\backend", shell=True)
        
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