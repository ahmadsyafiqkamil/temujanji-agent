from collections.abc import AsyncGenerator

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.auth import hash_password
from backend.app.config import settings
from backend.app.models import StaffRole, StaffUser, utc_now

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def bootstrap_admin() -> None:
    # Called from backend/app/main.py lifespan. Fixes INSERT via sqlalchemy
    # core which skips SQLModel default_factory for created_at/updated_at.
    # User: "jalankan aplikasinya sekarang"
    async with SessionLocal() as session:
        now = utc_now()
        statement = (
            insert(StaffUser)
            .values(
                username="admin",
                password_hash=hash_password(settings.admin_bootstrap_password),
                role=StaffRole.ADMIN,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["username"])
        )
        await session.execute(statement)
        await session.commit()
