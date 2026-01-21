# app/database.py
from sqlmodel import create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings

# Synchronous engine – used by Alembic and sync tasks
engine = create_engine(
    settings.DB_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,  # Keeps connections healthy in Docker
    # Removed: connect_args={"server_settings": {"jit": "off"}}  ← This caused the error
)

# Async engine – for FastAPI async routes/websockets
async_engine = create_async_engine(
    settings.ASYNC_DB_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(async_engine, expire_on_commit=False)


# Synchronous session factory – safe and simple
def get_session() -> Session:
    """Return a new Session for use in 'with' blocks."""
    return Session(engine)


# Async session dependency – for FastAPI
async def get_async_session():
    async with async_session() as session:
        yield session