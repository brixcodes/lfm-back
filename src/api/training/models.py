from sqlmodel import Field, Relationship
from datetime import date
from src.api.user.models import User
from src.helper.model import CustomBaseUUIDModel, CustomBaseModel
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, JSON, Numeric

class TrainingTypeEnum(str, Enum):
    ON_SITE = "On-Site"
    OFF_SITE = "Off-Site"

class TrainingStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class DurationEnum(str, Enum):
    MONTHS = "MONTHS"
    YEARS = "YEARS"
    DAYS = "DAYS"
    HOURS = "HOURS"

class TrainingSessionStatusEnum(str, Enum):
    OPEN_FOR_REGISTRATION = "OPEN_FOR_REGISTRATION"
    CLOSE_FOR_REGISTRATION = "CLOSE_FOR_REGISTRATION"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"

class Training(CustomBaseUUIDModel, table=True):
    __tablename__ = "trainings"
    
    title: str 
    status: str = Field(default=TrainingStatusEnum.ACTIVE)
    
    duration: int = Field(default=0)
    duration_unit: str = Field(default=DurationEnum.HOURS)
    
    specialty_id: int = Field(foreign_key="specialty.id")
    info_sheet: Optional[str] = Field(default=None, max_length=255)  # lien vers la fiche d'info
    training_type: str = Field(default=TrainingTypeEnum.ON_SITE)
    presentation: str = Field(default="", description="Context, challenges, and overall vision of the training")
    
    # JSON columns
    benefits: Optional[List[Dict[str, str]]] = Field(default=None, sa_column=Column(JSON))
    strengths: Optional[List[Dict[str, str]]] = Field(default=None, sa_column=Column(JSON))
    
    target_skills: str = Field(default="", description="Skills and know-how to be acquired")
    program: str = Field(default="", description="Detailed content and structure of the training")
    target_audience: str = Field(default="", description="Intended audience and prerequisites")
    prerequisites: Optional[str] = Field(default=None)
    enrollment: str = Field(default="", description="Enrollment methods, duration, pace")

class TrainingSession(CustomBaseUUIDModel, table=True):
    __tablename__ = "training_sessions"

    training_id: str = Field(foreign_key="trainings.id", nullable=False)
    center_id: Optional[int] = Field(default=None, foreign_key="organization_centers.id", nullable=True)

    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)
    registration_deadline: date 
    available_slots: Optional[int] = Field(default=None, description="Number of available places")

    status: str = Field(default=TrainingSessionStatusEnum.OPEN_FOR_REGISTRATION, nullable=False)

    registration_fee: Optional[float] = Field(default=None, sa_column=Column(Numeric(12, 2)))
    training_fee: Optional[float] = Field(default=None, sa_column=Column(Numeric(12, 2)))
    
    currency: str = Field(default="EUR")
    
    required_attachments: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    installment_percentage: Optional[List[float]] = Field(default=None, sa_column=Column(JSON))
    
    moodle_course_id: Optional[int] = Field(default=None, description="Linked Moodle course id")
    
    # Relationships
    training: Optional[Training] = Relationship()

class TrainingSessionParticipant(CustomBaseModel, table=True):
    __tablename__ = "training_session_participants"

    session_id: str = Field(foreign_key="training_sessions.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    application_id: Optional[int] = Field(default=None, index=True, unique=True)
    
    # Relationships
    training_session: Optional[TrainingSession] = Relationship()
    user: Optional[User] = Relationship()
    


class ApplicationStatusEnum(str, Enum):
    RECEIVED = "RECEIVED"
    SUBMITTED = "SUBMITTED"
    REFUSED = "REFUSED"
    APPROVED = "APPROVED"

class StudentApplication(CustomBaseModel, table=True):
    __tablename__ = "student_applications"
    
    user_id: str = Field(foreign_key="users.id", nullable=False)
    training_id: str = Field(foreign_key="trainings.id")
    target_session_id: str = Field(foreign_key="training_sessions.id")
    application_number: str = Field(default=None, max_length=50, index=True, unique=True)
    status: str = Field(default=ApplicationStatusEnum.RECEIVED)
    refusal_reason: Optional[str] = Field(default=None)
    registration_fee: Optional[float] = Field(default=None, sa_column=Column(Numeric(12, 2)))
    training_fee: Optional[float] = Field(default=None, sa_column=Column(Numeric(12, 2)))
    currency: str = Field(default="EUR")
    installment_percentage: Optional[List[float]] = Field(default=None, sa_column=Column(JSON))
    payment_id : Optional[str] = Field(default=None,foreign_key="payments.id", nullable=True)

    training: Training = Relationship()
    training_session: TrainingSession = Relationship()
    user: User = Relationship()
    
    attachments: List["StudentAttachment"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class StudentAttachment(CustomBaseModel, table=True):
    __tablename__ = "student_attachments"

    application_id: int = Field(foreign_key="student_applications.id", nullable=False)
    document_type: str = Field(max_length=100)
    file_path: str = Field(max_length=255)
    upload_date: Optional[datetime] = Field(default=None)


class TrainingFeeInstallmentPayment(CustomBaseModel, table=True):
    __tablename__ = "training_fee_installment_payments"
    
    User_id: str = Field(foreign_key="users.id", nullable=False)
    training_session_id: str = Field(foreign_key="training_sessions.id", nullable=False)
    application_id: int = Field(foreign_key="student_applications.id", nullable=False)
    payment_id: Optional[str] = Field(foreign_key="payments.id", nullable=True)
    installment_number: int
    amount: float
    rest_to_pay: float
    currency: str


class Specialty(CustomBaseModel, table=True):
    __tablename__ = "specialty"
    
    name: str
    description: Optional[str] = Field(default="")
    

class ReclamationStatusEnum(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"

class ReclamationPriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ReclamationType(CustomBaseModel, table=True):
    __tablename__ = "reclamation_types"
    name: str
    description: Optional[str] = Field(default=None)

class Reclamation(CustomBaseModel, table=True):
    __tablename__ = "reclamations"
    
    admin_id: Optional[str] = Field(foreign_key="users.id", nullable=True)
    reclamation_number: str = Field(max_length=50, index=True, unique=True)
    application_number: str = Field(max_length=50, index=True)
    subject: str = Field(max_length=255)
    reclamation_type: int = Field(foreign_key="reclamation_types.id", nullable=False)
    priority: str = Field(default=ReclamationPriorityEnum.LOW, max_length=10)
    status: str = Field(max_length=10, default=ReclamationStatusEnum.NEW)
    description: str = Field(default="")
    closure_date: Optional[datetime] = Field(default=None, nullable=True, sa_type=TIMESTAMP(timezone=True))