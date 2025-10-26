from datetime import date, datetime
from typing import List, Optional, Literal
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr, Field
from src.api.job_offers.models import ApplicationStatusEnum
from src.api.training.models import DurationEnum, ReclamationPriorityEnum, ReclamationStatusEnum, TrainingSessionStatusEnum, TrainingStatusEnum, TrainingTypeEnum
from src.helper.schemas import BaseOutPage, BaseOutSuccess

class StrengthInput(BaseModel):
    image: str
    content: str
    
class BenefitInput(BaseModel):
    image: str
    content: str
    url: str

class ChangeStudentApplicationStatusInput(BaseModel):
    status : str
    reason : str


# Training Schemas
class TrainingCreateInput(BaseModel):
    title: str
    status: TrainingStatusEnum = TrainingStatusEnum.ACTIVE
    duration: int = 0
    duration_unit: DurationEnum = DurationEnum.HOURS
    specialty_id: int
    info_sheet: Optional[str] = None
    training_type: TrainingTypeEnum
    presentation: Optional[str] = ""
    benefits: Optional[List[BenefitInput]] = None
    strengths: Optional[List[StrengthInput]] = None
    target_skills: Optional[str] = ""
    program: Optional[str] = ""
    target_audience: Optional[str] = ""
    prerequisites: Optional[str] = None
    enrollment: Optional[str] = ""

class TrainingUpdateInput(BaseModel):
    title: Optional[str] = None
    status: Optional[TrainingStatusEnum] = None
    duration: Optional[int] = None
    duration_unit: Optional[DurationEnum] = None
    specialty_id: Optional[int] = None
    info_sheet: Optional[str] = None
    training_type: Optional[TrainingTypeEnum] = None
    presentation: Optional[str] = None
    benefits: Optional[List[BenefitInput]] = None
    strengths: Optional[List[StrengthInput]] = None
    target_skills: Optional[str] = None
    program: Optional[str] = None
    target_audience: Optional[str] = None
    prerequisites: Optional[str] = None
    enrollment: Optional[str] = None

class TrainingOut(BaseModel):
    id: str
    title: str
    status: str
    duration: int
    duration_unit: str
    specialty_id: int
    info_sheet: Optional[str]
    training_type: str
    presentation: str
    benefits: Optional[List[BenefitInput]]
    strengths: Optional[List[StrengthInput]]
    target_skills: str
    program: str
    target_audience: str
    prerequisites: Optional[str]
    enrollment: str
    created_at: datetime
    updated_at: datetime

class TrainingFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    status: Optional[str] = None
    specialty_id: Optional[int] = None
    order_by: Literal["created_at", "title"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"

# Training Session Schemas
class TrainingSessionCreateInput(BaseModel):
    training_id: str
    center_id: Optional[int] = None
    start_date: date
    end_date: date
    registration_deadline: date
    available_slots: int
    status: TrainingSessionStatusEnum
    registration_fee: float
    training_fee: float
    currency: str = "EUR"

class TrainingSessionUpdateInput(BaseModel):
    center_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    registration_deadline: Optional[date] = None
    available_slots: Optional[int] = None
    status: Optional[TrainingSessionStatusEnum] = None
    registration_fee: Optional[float] = None
    training_fee: Optional[float] = None
    currency: Optional[str] = None

class TrainingSessionOut(BaseModel):
    id: str
    training_id: str
    center_id: Optional[int]
    start_date: Optional[date]
    end_date: Optional[date]
    registration_deadline: date
    available_slots: Optional[int]
    status: str
    registration_fee: Optional[float]
    training_fee: Optional[float]
    currency: str
    moodle_course_id: Optional[int]
    created_at: datetime
    updated_at: datetime

class TrainingSessionFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    training_id: Optional[str] = None
    center_id: Optional[int] = None
    status: Optional[str] = None
    order_by: Literal["created_at", "registration_deadline", "start_date"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"

# Success Response Schemas
class TrainingOutSuccess(BaseOutSuccess):
    data: TrainingOut

class TrainingsPageOutSuccess(BaseOutPage):
    data: List[TrainingOut]

class TrainingSessionOutSuccess(BaseOutSuccess):
    data: TrainingSessionOut

class TrainingSessionsPageOutSuccess(BaseOutPage):
    data: List[TrainingSessionOut]
    

class PayTrainingFeeInstallmentInput(BaseModel):
    training_session_id: str
    amount: float

# Specialty Schemas
class SpecialtyCreateInput(BaseModel):
    name: str
    description: str = ""

class SpecialtyUpdateInput(BaseModel):
    name: str
    description: str = ""

class SpecialtyOut(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

class SpecialtyFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    order_by: Literal["created_at", "name"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"

# Specialty Success Response Schemas
class SpecialtyOutSuccess(BaseOutSuccess):
    data: SpecialtyOut

class SpecialtyListOutSuccess(BaseOutSuccess):
    data: List[SpecialtyOut]

class SpecialtiesPageOutSuccess(BaseOutPage):
    data: List[SpecialtyOut]
    
    


class StudentApplicationFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    training_id: Optional[str] = None
    training_session_id: Optional[str] = None
    is_paid: Optional[bool] = True
    status: Optional[str] = None
    order_by: Literal["created_at"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"

# Student Application and Attachments
class StudentAttachmentInput(BaseModel):
    name: str
    file: UploadFile

class StudentAttachmentOut(BaseModel):
    id: int
    application_id: int
    document_type: str
    file_path: str
    created_at: datetime
    updated_at: datetime

class StudentApplicationCreateInput(BaseModel):
    email: EmailStr
    target_session_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    attachments: Optional[List[str]] = None

class StudentApplicationUpdateInput(BaseModel):
    status: Optional[ApplicationStatusEnum] = None
    refusal_reason: Optional[str] = None

class StudentApplicationSubmitInput(BaseModel):
    application_id: int
    target_session_id: str

class StudentApplicationOut(BaseModel):
    id: int
    user_id: str
    training_id: str
    target_session_id: str
    application_number: str
    status: str
    payment_id : Optional[str]
    refusal_reason: Optional[str]
    registration_fee: Optional[float]
    training_fee: Optional[float]
    currency: str
    training_title: str
    training_session_start_date: date
    training_session_end_date: date
    user_email: str
    user_first_name: str
    user_last_name: str

    created_at: datetime
    updated_at: datetime

class StudentApplicationFullOut(BaseModel):
    id: int
    user_id: str
    training_id: str
    target_session_id: str
    application_number: str
    status: str
    refusal_reason: Optional[str]
    registration_fee: Optional[float]
    training_fee: Optional[float]
    currency: str
    created_at: datetime
    updated_at: datetime
    payment_id : Optional[str]
    training: Optional[TrainingOut] = None
    training_session: Optional[TrainingSessionOut] = None
    # user: Optional[UserOut] = None  # Import from system schemas if needed

# Success Response Schemas
class StudentApplicationOutSuccess(BaseOutSuccess):
    data: StudentApplicationFullOut

class StudentApplicationsPageOutSuccess(BaseOutPage):
    data: List[StudentApplicationOut]

class StudentAttachmentOutSuccess(BaseOutSuccess):
    data: StudentAttachmentOut

class StudentAttachmentListOutSuccess(BaseOutSuccess):
    data: List[StudentAttachmentOut]
    

# Reclamation Schemas
class ReclamationCreateInput(BaseModel):
    application_number: str
    subject: str
    reclamation_type: int
    priority: ReclamationPriorityEnum = ReclamationPriorityEnum.LOW
    description: str

class ReclamationUpdateStatusInput(BaseModel):
    status: ReclamationStatusEnum
    admin_id: Optional[str] = None

class ReclamationAdminUpdateInput(BaseModel):
    status: Optional[ReclamationStatusEnum] = None
    

class ReclamationOut(BaseModel):
    id: int
    admin_id: Optional[str]
    reclamation_number: str
    application_number: str
    subject: str
    reclamation_type: int
    priority: str
    status: str
    description: str
    closure_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class ReclamationFullOut(BaseModel):
    id: int
    admin_id: Optional[str]
    reclamation_number: str
    application_number: str
    subject: str
    reclamation_type: int
    priority: str
    status: str
    description: str
    closure_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Relationships (optional for full details)
    admin_name: Optional[str] = None
    reclamation_type_name: Optional[str] = None

class ReclamationFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    status: Optional[ReclamationStatusEnum] = None
    priority: Optional[ReclamationPriorityEnum] = None
    reclamation_type: Optional[int] = None
    admin_id: Optional[str] = None
    application_number: Optional[str] = None
    order_by: Literal["created_at", "subject", "priority"] = "created_at"
    asc: Literal["asc", "desc"] = "desc"

# Reclamation Type Schemas
class ReclamationTypeUpdateInput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ReclamationTypeCreateInput(BaseModel):
    name: str
    description: Optional[str] = None

class ReclamationTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

# Reclamation Success Response Schemas
class ReclamationOutSuccess(BaseOutSuccess):
    data: ReclamationFullOut

class ReclamationListOutSuccess(BaseOutSuccess):
    data: List[ReclamationOut]

class ReclamationsPageOutSuccess(BaseOutPage):
    data: List[ReclamationOut]

class ReclamationTypeOutSuccess(BaseOutSuccess):
    data: ReclamationTypeOut

class ReclamationTypeListOutSuccess(BaseOutSuccess):
    data: List[ReclamationTypeOut]
    

