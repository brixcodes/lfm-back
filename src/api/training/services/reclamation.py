from typing import List, Optional, Tuple
from datetime import datetime, timezone
from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_

from src.database import get_session_async
from src.api.training.models import (
    Reclamation,
    ReclamationType,
    ReclamationStatusEnum,
    StudentApplication,
)
from src.api.training.schemas import (
    ReclamationCreateInput,
    ReclamationFilter,
    ReclamationAdminUpdateInput,
    ReclamationTypeCreateInput,
    ReclamationTypeUpdateInput,
)

class ReclamationService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    # Reclamation CRUD Operations
    async def create_reclamation(self, data: ReclamationCreateInput, user_id: str) -> Reclamation:
        """Create a new reclamation by user"""
        # Generate reclamation number: REC-{seq}-{YYYYMMDDHHMMSS}
        count_stmt = select(func.count(Reclamation.id))
        count_res = await self.session.execute(count_stmt)
        seq = (count_res.scalar() or 0) + 1
        reclamation_number = f"REC-{seq:04d}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        reclamation = Reclamation(
            reclamation_number=reclamation_number,
            application_number=data.application_number,
            subject=data.subject,
            reclamation_type=data.reclamation_type,
            priority=data.priority,
            description=data.description,
            status=ReclamationStatusEnum.NEW
        )
        self.session.add(reclamation)
        await self.session.commit()
        await self.session.refresh(reclamation)
        return reclamation

    async def get_reclamation_by_id(self, reclamation_id: int, user_id: Optional[str] = None) -> Optional[Reclamation]:
        """Get reclamation by ID, optionally filtered by user"""
        statement = select(Reclamation).where(
            Reclamation.id == reclamation_id,
            Reclamation.delete_at.is_(None)
        )
        
        # If user_id provided, ensure user can only access their own reclamations
        if user_id is not None:
            statement = (
                statement
                .join(StudentApplication, StudentApplication.application_number == Reclamation.application_number)
                .where(StudentApplication.user_id == user_id)
            )
        
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_user_reclamations(self, user_id: str, filters: ReclamationFilter) -> Tuple[List[Reclamation], int]:
        """List reclamations for a specific user with pagination"""
        statement = (
            select(Reclamation)
            .join(StudentApplication, StudentApplication.application_number == Reclamation.application_number)
            .where(StudentApplication.user_id == user_id, Reclamation.delete_at.is_(None))
        )
        
        
        count_query = (
            select(func.count(Reclamation.id))
            .join(StudentApplication, StudentApplication.application_number == Reclamation.application_number)
            .where(StudentApplication.user_id == user_id, Reclamation.delete_at.is_(None))
        )

        # Apply search filter
        if filters.search is not None:
            search_filter = or_(
                Reclamation.subject.contains(filters.search),
                Reclamation.description.contains(filters.search),
                Reclamation.reclamation_number.contains(filters.search),
                Reclamation.application_number.contains(filters.search)
            )
            statement = statement.where(search_filter)
            count_query = count_query.where(search_filter)

        # Apply status filter
        if filters.status is not None:
            statement = statement.where(Reclamation.status == filters.status)
            count_query = count_query.where(Reclamation.status == filters.status)

        # Apply priority filter
        if filters.priority is not None:
            statement = statement.where(Reclamation.priority == filters.priority)
            count_query = count_query.where(Reclamation.priority == filters.priority)

        # Apply ordering
        if filters.order_by == "created_at":
            statement = statement.order_by(
                Reclamation.created_at if filters.asc == "asc" else Reclamation.created_at.desc()
            )
        elif filters.order_by == "subject":
            statement = statement.order_by(
                Reclamation.subject if filters.asc == "asc" else Reclamation.subject.desc()
            )
        elif filters.order_by == "priority":
            statement = statement.order_by(
                Reclamation.priority if filters.asc == "asc" else Reclamation.priority.desc()
            )

        # Get total count
        total_count = (await self.session.execute(count_query)).scalar_one()

        # Apply pagination
        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def list_all_reclamations(self, filters: ReclamationFilter) -> Tuple[List[Reclamation], int]:
        """List all reclamations for admin with pagination and filtering"""
        statement = select(Reclamation).where(Reclamation.delete_at.is_(None))
        count_query = select(func.count(Reclamation.id)).where(Reclamation.delete_at.is_(None))

        # Apply search filter
        if filters.search is not None:
            search_filter = or_(
                Reclamation.subject.contains(filters.search),
                Reclamation.description.contains(filters.search),
                Reclamation.reclamation_number.contains(filters.search),
                Reclamation.application_number.contains(filters.search)
            )
            statement = statement.where(search_filter)
            count_query = count_query.where(search_filter)

        # Apply filters
        if filters.status is not None:
            statement = statement.where(Reclamation.status == filters.status)
            count_query = count_query.where(Reclamation.status == filters.status)
            
        if filters.priority is not None:
            statement = statement.where(Reclamation.priority == filters.priority)
            count_query = count_query.where(Reclamation.priority == filters.priority)
            
        if filters.reclamation_type is not None:
            statement = statement.where(Reclamation.reclamation_type == filters.reclamation_type)
            count_query = count_query.where(Reclamation.reclamation_type == filters.reclamation_type)
            
        if filters.admin_id is not None:
            statement = statement.where(Reclamation.admin_id == filters.admin_id)
            count_query = count_query.where(Reclamation.admin_id == filters.admin_id)
            
        if filters.application_number is not None:
            statement = statement.where(Reclamation.application_number == filters.application_number)
            count_query = count_query.where(Reclamation.application_number == filters.application_number)

        # Apply ordering
        if filters.order_by == "created_at":
            statement = statement.order_by(
                Reclamation.created_at if filters.asc == "asc" else Reclamation.created_at.desc()
            )
        elif filters.order_by == "subject":
            statement = statement.order_by(
                Reclamation.subject if filters.asc == "asc" else Reclamation.subject.desc()
            )
        elif filters.order_by == "priority":
            statement = statement.order_by(
                Reclamation.priority if filters.asc == "asc" else Reclamation.priority.desc()
            )

        # Get total count
        total_count = (await self.session.execute(count_query)).scalar_one()

        # Apply pagination
        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def update_reclamation_status(self, reclamation: Reclamation, data: ReclamationAdminUpdateInput) -> Reclamation:
        """Update reclamation status and other admin fields"""
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(reclamation, key, value)
            
        # Set closure date if status is CLOSED
        if data.status == ReclamationStatusEnum.CLOSED:
            reclamation.closure_date = datetime.now(timezone.utc)
            
        self.session.add(reclamation)
        await self.session.commit()
        await self.session.refresh(reclamation)
        return reclamation

    async def update_reclamation(self, reclamation_id: int, data: ReclamationCreateInput, user_id: str) -> Reclamation:
        """Update a reclamation by user"""
        # Get the reclamation
        reclamation = await self.get_reclamation_by_id(reclamation_id, user_id)
        if not reclamation:
            raise ValueError("Reclamation not found")
        
        # Update the reclamation fields
        reclamation.application_number = data.application_number
        reclamation.reclamation_type = data.reclamation_type
        reclamation.subject = data.subject
        reclamation.priority = data.priority
        reclamation.description = data.description
        reclamation.updated_at = datetime.now(timezone.utc)
        
        self.session.add(reclamation)
        await self.session.commit()
        await self.session.refresh(reclamation)
        return reclamation

    async def delete_reclamation(self, reclamation: Reclamation) -> Reclamation:
        """Soft delete reclamation"""
        reclamation.delete_at = datetime.now(timezone.utc)
        self.session.add(reclamation)
        await self.session.commit()
        return reclamation

    # Reclamation Type Operations
    async def create_reclamation_type(self, data: ReclamationTypeCreateInput) -> ReclamationType:
        """Create a new reclamation type"""
        reclamation_type = ReclamationType(**data.model_dump())
        self.session.add(reclamation_type)
        await self.session.commit()
        await self.session.refresh(reclamation_type)
        return reclamation_type
    
    async def update_reclamation_type(self, reclamation_type: ReclamationType, data: ReclamationTypeUpdateInput) -> ReclamationType:
        """Update reclamation type"""
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(reclamation_type, key, value)
        self.session.add(reclamation_type)
        await self.session.commit()
        await self.session.refresh(reclamation_type)
        return reclamation_type

    async def get_reclamation_type_by_id(self, type_id: int) -> Optional[ReclamationType]:
        """Get reclamation type by ID"""
        statement = select(ReclamationType).where(
            ReclamationType.id == type_id,
            ReclamationType.delete_at.is_(None)
        )
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def delete_reclamation_type(self, type_id: int) -> ReclamationType:
        """Soft delete reclamation type"""
        reclamation_type = await self.get_reclamation_type_by_id(type_id)
        if not reclamation_type:
            raise ValueError("Reclamation type not found")
        
        reclamation_type.delete_at = datetime.now(timezone.utc)
        self.session.add(reclamation_type)
        await self.session.commit()
        await self.session.refresh(reclamation_type)
        return reclamation_type

    async def get_all_reclamation_types(self) -> List[ReclamationType]:
        """Get all active reclamation types for dropdown lists"""
        statement = select(ReclamationType).where(
            ReclamationType.delete_at.is_(None)
        ).order_by(ReclamationType.name)
        result = await self.session.execute(statement)
        return result.scalars().all()