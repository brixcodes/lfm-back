from typing import List, Optional, Tuple
from datetime import datetime, timezone
from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_

from src.api.user.models import User
from src.database import get_session_async
from src.api.training.models import (
    Training,
    TrainingSession,
    TrainingSessionParticipant,
)
from src.api.training.schemas import (
    TrainingCreateInput,
    TrainingUpdateInput,
    TrainingFilter,
    TrainingSessionCreateInput,
    TrainingSessionUpdateInput,
    TrainingSessionFilter,
)
from src.helper.moodle import MoodleService

try:
    from src.helper.moodle import moodle_create_course_task
except Exception:
    moodle_create_course_task = None

class TrainingService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    # Training CRUD Operations
    async def create_training(self, data: TrainingCreateInput) -> Training:
        """Create a new training"""
        training = Training(**data.model_dump(exclude_none=True))
        self.session.add(training)
        await self.session.commit()
        await self.session.refresh(training)
        return training

    async def update_training(self, training: Training, data: TrainingUpdateInput) -> Training:
        """Update training"""
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(training, key, value)
        self.session.add(training)
        await self.session.commit()
        await self.session.refresh(training)
        return training

    async def get_training_by_id(self, training_id: str) -> Optional[Training]:
        """Get training by ID"""
        statement = select(Training).where(Training.id == training_id, Training.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_trainings(self, filters: TrainingFilter) -> Tuple[List[Training], int]:
        """List trainings with pagination and filtering"""
        statement = select(Training).where(Training.delete_at.is_(None))
        count_query = select(func.count(Training.id)).where(Training.delete_at.is_(None))

        # Apply search filter
        if filters.search is not None:
            like_clause = or_(
                Training.title.contains(filters.search),
                Training.presentation.contains(filters.search),
                Training.program.contains(filters.search),
                Training.target_skills.contains(filters.search),
            )
            statement = statement.where(like_clause)
            count_query = count_query.where(like_clause)

        # Apply filters
        if filters.status is not None:
            statement = statement.where(Training.status == filters.status)
            count_query = count_query.where(Training.status == filters.status)

        if filters.specialty_id is not None:
            statement = statement.where(Training.specialty_id == filters.specialty_id)
            count_query = count_query.where(Training.specialty_id == filters.specialty_id)

        # Apply ordering
        if filters.order_by == "created_at":
            statement = statement.order_by(Training.created_at if filters.asc == "asc" else Training.created_at.desc())
        elif filters.order_by == "title":
            statement = statement.order_by(Training.title if filters.asc == "asc" else Training.title.desc())

        total_count = (await self.session.execute(count_query)).scalar_one()

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def delete_training(self, training: Training) -> Training:
        """Soft delete training"""
        training.delete_at = datetime.now(timezone.utc)
        self.session.add(training)
        await self.session.commit()
        return training

    # Training Session CRUD Operations
    async def create_training_session(self, data: TrainingSessionCreateInput) -> TrainingSession:
        """Create a new training session"""
        session = TrainingSession(**data.model_dump(exclude_none=True))
        
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        
        # Create Moodle course (best-effort)
        try:
            # Fetch training for names
            tr_stmt = select(Training).where(Training.id == session.training_id)
            tr_res = await self.session.execute(tr_stmt)
            training = tr_res.scalars().first()
            # Format dates (use only if available)
            start_str = session.start_date.strftime("%B %Y") if session.start_date else "Undated"
            cohort = f"Cohort {session.id[:6].upper()}"  # short unique label

            fullname = f"{training.title} – {start_str} {cohort}"
            shortname = f"{training.title[:20]}-{session.start_date.strftime('%b%y') if session.start_date else session.id[:4]}"
                    
            if moodle_create_course_task:
                moodle_create_course_task.apply_async(kwargs={"fullname": fullname, "shortname": shortname})
            else:
                moodle = MoodleService()
                course_id = await moodle.create_course(fullname=fullname, shortname=shortname)
                session.moodle_course_id = course_id
                self.session.add(session)
                await self.session.commit()
                await self.session.refresh(session)
        except Exception:
            pass
            
        return session

    async def update_training_session(self, training_session: TrainingSession, data: TrainingSessionUpdateInput) -> TrainingSession:
        """Update training session"""
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(training_session, key, value)
        self.session.add(training_session)
        await self.session.commit()
        await self.session.refresh(training_session)
        return training_session

    async def get_training_session_by_id(self, session_id: str) -> Optional[TrainingSession]:
        """Get training session by ID"""
        statement = select(TrainingSession).where(TrainingSession.id == session_id, TrainingSession.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_training_sessions(self, filters: TrainingSessionFilter) -> Tuple[List[TrainingSession], int]:
        """List training sessions with pagination and filtering"""
        statement = select(TrainingSession).where(TrainingSession.delete_at.is_(None))
        count_query = select(func.count(TrainingSession.id)).where(TrainingSession.delete_at.is_(None))

        # Apply filters
        if filters.training_id is not None:
            statement = statement.where(TrainingSession.training_id == filters.training_id)
            count_query = count_query.where(TrainingSession.training_id == filters.training_id)

        if filters.center_id is not None:
            statement = statement.where(TrainingSession.center_id == filters.center_id)
            count_query = count_query.where(TrainingSession.center_id == filters.center_id)

        if filters.status is not None:
            statement = statement.where(TrainingSession.status == filters.status)
            count_query = count_query.where(TrainingSession.status == filters.status)

        # Apply ordering
        if filters.order_by == "created_at":
            statement = statement.order_by(TrainingSession.created_at if filters.asc == "asc" else TrainingSession.created_at.desc())
        elif filters.order_by == "registration_deadline":
            statement = statement.order_by(TrainingSession.registration_deadline if filters.asc == "asc" else TrainingSession.registration_deadline.desc())
        elif filters.order_by == "start_date":
            statement = statement.order_by(TrainingSession.start_date if filters.asc == "asc" else TrainingSession.start_date.desc())

        total_count = (await self.session.execute(count_query)).scalar_one()

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def delete_training_session(self, training_session: TrainingSession) -> TrainingSession:
        """Soft delete training session"""
        training_session.delete_at = datetime.now(timezone.utc)
        self.session.add(training_session)
        await self.session.commit()
        return training_session
    
    
    async def get_training_session_members(self, session_id: str) -> List[User]:
        statement = select(User).join(TrainingSessionParticipant, User.id == TrainingSessionParticipant.user_id).where(TrainingSessionParticipant.session_id == session_id)
        result = await self.session.execute(statement)
        return result.scalars().all()