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

class ReclamationPriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class ReclamationStatusEnum(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

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
    prerequisites: str = Field(default="", description="Required prerequisites and conditions")
    enrollment: str = Field(default="", description="Additional information and notes")
    
    # Relationships
    specialty: "Specialty" = Relationship()
    training_sessions: List["TrainingSession"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class TrainingSession(CustomBaseUUIDModel, table=True):
    __tablename__ = "training_sessions"
    
    training_id: str = Field(foreign_key="trainings.id")
    start_date: date
    end_date: date
    status: str = Field(default=TrainingSessionStatusEnum.OPEN_FOR_REGISTRATION)
    max_participants: int = Field(default=0)
    registration_fee: Optional[float] = Field(default=None, sa_column=Column(Numeric(12, 2)))
    training_fee: Optional[float] = Field(default=None, sa_column=Column(Numeric(12, 2)))
    currency: str = Field(default="XOF")
    
    # Relationships
    training: Training = Relationship()
    participants: List["TrainingSessionParticipant"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class TrainingSessionParticipant(CustomBaseModel, table=True):
    __tablename__ = "training_session_participants"
    
    training_session_id: str = Field(foreign_key="training_sessions.id")
    user_id: str = Field(foreign_key="users.id")
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    training_session: TrainingSession = Relationship()
    user: User = Relationship()

class ApplicationStatusEnum(str, Enum):
    RECEIVED = "RECEIVED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REFUSED = "REFUSED"

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
    
    # Additional fields for frontend alignment
    payment_method: Optional[str] = Field(default=None, max_length=20)
    civility: Optional[str] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    date_of_birth: Optional[str] = Field(default=None, max_length=20)

    training: Training = Relationship()
    training_session: TrainingSession = Relationship()
    user: User = Relationship()
    
    attachments: List["StudentAttachment"] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class StudentAttachment(CustomBaseModel, table=True):
    __tablename__ = "student_attachments"
    
    student_application_id: int = Field(foreign_key="student_applications.id")
    attachment_type: str = Field(max_length=50)
    file_path: str = Field(max_length=255)
    file_name: str = Field(max_length=255)
    file_size: Optional[int] = Field(default=None)
    mime_type: Optional[str] = Field(default=None, max_length=100)
    
    # Relationships
    student_application: StudentApplication = Relationship()

class Specialty(CustomBaseModel, table=True):
    __tablename__ = "specialty"
    
    name: str = Field(max_length=100, unique=True)
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Relationships
    trainings: List[Training] = Relationship(sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class TrainingFeeInstallmentPayment(CustomBaseModel, table=True):
    __tablename__ = "training_fee_installment_payments"
    
    student_application_id: int = Field(foreign_key="student_applications.id")
    installment_number: int = Field(default=1)
    amount: float = Field(sa_column=Column(Numeric(12, 2)))
    currency: str = Field(default="XOF")
    due_date: date
    payment_status: str = Field(default="PENDING")
    payment_date: Optional[datetime] = Field(default=None)
    payment_reference: Optional[str] = Field(default=None, max_length=100)
    
    # Relationships
    student_application: StudentApplication = Relationship()

class Reclamation(CustomBaseModel, table=True):
    __tablename__ = "reclamations"
    
    user_id: str = Field(foreign_key="users.id")
    title: str = Field(max_length=200)
    
    description: str = Field(max_length=1000)
    priority: str = Field(default=ReclamationPriorityEnum.MEDIUM)
    status: str = Field(default=ReclamationStatusEnum.OPEN)
    resolution_notes: Optional[str] = Field(default=None, max_length=1000)
    resolved_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    user: User = Relationship()

class ReclamationType(CustomBaseModel, table=True):
    __tablename__ = "reclamation_types"
    
    name: str = Field(max_length=100, unique=True)
    description: Optional[str] = Field(default=None, max_length=500)
