from contextlib import contextmanager
from sqlmodel import create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from typing import AsyncGenerator
from src.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)



@contextmanager
def get_session():
    with Session(engine) as session:
        yield session

DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine_async = create_async_engine(DATABASE_URL )#echo=True)
async_session = sessionmaker(engine_async, class_=AsyncSession, expire_on_commit=False)

async def get_session_async() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session