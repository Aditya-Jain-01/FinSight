from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Only for non-streaming routes (e.g. create_thread). The streaming chat route
    opens its own session directly via async_session_maker — see chat_service.py."""
    async with async_session_maker() as session:
        yield session
        await session.commit()