from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency that yields an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables. For development use only."""
    from app.models.base import Base
    # Import all models so they register with Base.metadata
    from app.models import (  # noqa: F401
        user_account, game_session, vlocation, computer, security,
        databank, logbank, person, player, connection, gateway,
        company, mission, message, running_task, scheduled_event,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
