from typing import List, Optional, Tuple
from datetime import datetime, timezone
from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_

from src.database import get_session_async
from src.api.training.models import Specialty
from src.api.training.schemas import (
    SpecialtyCreateInput,
    SpecialtyUpdateInput,
    SpecialtyFilter,
)

class SpecialtyService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    async def create_specialty(self, data: SpecialtyCreateInput) -> Specialty:
        """Create a new specialty"""
        specialty = Specialty(**data.model_dump())
        self.session.add(specialty)
        await self.session.commit()
        await self.session.refresh(specialty)
        return specialty

    async def get_specialty_by_id(self, specialty_id: int) -> Optional[Specialty]:
        """Get specialty by ID"""
        statement = select(Specialty).where(
            Specialty.id == specialty_id,
            Specialty.delete_at.is_(None)
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_specialty_by_name(self, name: str) -> Optional[Specialty]:
        """Get specialty by name"""
        statement = select(Specialty).where(
            Specialty.name == name,
            Specialty.delete_at.is_(None)
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_specialties(self, filters: SpecialtyFilter) -> Tuple[List[Specialty], int]:
        """List specialties with pagination and filtering"""
        statement = select(Specialty).where(Specialty.delete_at.is_(None))
        count_query = select(func.count(Specialty.id)).where(Specialty.delete_at.is_(None))

        # Apply search filter
        if filters.search is not None:
            search_filter = or_(
                Specialty.name.contains(filters.search),
                Specialty.description.contains(filters.search)
            )
            statement = statement.where(search_filter)
            count_query = count_query.where(search_filter)

        # Apply ordering
        if filters.order_by == "created_at":
            statement = statement.order_by(
                Specialty.created_at if filters.asc == "asc" else Specialty.created_at.desc()
            )
        elif filters.order_by == "name":
            statement = statement.order_by(
                Specialty.name if filters.asc == "asc" else Specialty.name.desc()
            )

        # Get total count
        total_count = (await self.session.execute(count_query)).scalar_one()

        # Apply pagination
        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def update_specialty(self, specialty: Specialty, data: SpecialtyUpdateInput) -> Specialty:
        """Update specialty"""
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(specialty, key, value)
        self.session.add(specialty)
        await self.session.commit()
        await self.session.refresh(specialty)
        return specialty

    async def delete_specialty(self, specialty: Specialty) -> Specialty:
        """Soft delete specialty"""
        specialty.delete_at = datetime.now(timezone.utc)
        self.session.add(specialty)
        await self.session.commit()
        return specialty

    async def get_all_active_specialties(self) -> List[Specialty]:
        """Get all active specialties for dropdown lists"""
        statement = select(Specialty).where(
            Specialty.delete_at.is_(None)
        ).order_by(Specialty.name)
        result = await self.session.execute(statement)
        return result.scalars().all()