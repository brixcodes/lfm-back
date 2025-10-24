from datetime import date, datetime
from typing import List, Optional, Literal
from fastapi import UploadFile
from pydantic import BaseModel, EmailStr, Field
from src.api.payments.schemas import InitPaymentOut
from src.helper.schemas import BaseOutPage, BaseOutSuccess
from src.api.job_offers.models import ApplicationStatusEnum


class JobOfferCreateInput(BaseModel):
    reference: str
    title: str
    location: str
    postal_code: str
    contract_type: str
    uncertain_term: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    weekly_hours: Optional[int] = None
    driving_license_required: bool = False
    submission_deadline: date
    main_mission: Optional[str] = None
    responsibilities: Optional[str] = None
    competencies: Optional[str] = None
    profile: Optional[str] = None
    salary: Optional[float] = None
    benefits: Optional[str] = None
    submission_fee: float
    currency: str = "EUR"
    attachment: Optional[List[str]] = None
    conditions: Optional[str] = None


class JobOfferUpdateInput(BaseModel):
    reference: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    postal_code: Optional[str] = None
    contract_type: Optional[str] = None
    uncertain_term: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    weekly_hours: Optional[int] = None
    driving_license_required: Optional[bool] = None
    submission_deadline: Optional[date] = None
    main_mission: Optional[str] = None
    responsibilities: Optional[str] = None
    competencies: Optional[str] = None
    profile: Optional[str] = None
    salary: Optional[float] = None
    benefits: Optional[str] = None
    submission_fee: Optional[float] = None
    currency: Optional[str] = None
    attachment: Optional[List[str]] = None
    conditions: Optional[str] = None


class JobOfferOut(BaseModel):
    id: str
    reference: str
    title: str
    location: str
    postal_code: str
    contract_type: str
    uncertain_term: bool
    start_date: Optional[date]
    end_date: Optional[date]
    weekly_hours: Optional[int]
    driving_license_required: bool
    submission_deadline: date
    main_mission: Optional[str]
    responsibilities: Optional[str]
    competencies: Optional[str]
    profile: Optional[str]
    salary: Optional[float]
    benefits: Optional[str]
    submission_fee: float
    currency: str
    attachment: Optional[List[str]]
    conditions: Optional[str]
    created_at: datetime
    updated_at: datetime


class JobOfferFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    order_by: Literal["created_at", "submission_deadline", "title", "salary"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"

class JobAttachmentInput(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    name: str
    file: UploadFile

class JobAttachmentInput2(BaseModel):

    name: str
    type: str
    url: str

class JobApplicationCreateInput(BaseModel):
    job_offer_id: str
    email: EmailStr
    phone_number: str
    first_name: str
    last_name: str
    civility: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    attachments : Optional[List[JobAttachmentInput2]]=None
    payment_method: Literal["ONLINE", "TRANSFER"] = "ONLINE"
    


class JobApplicationUpdateInput(BaseModel):
    status: Optional[str] = None
    refusal_reason: Optional[str] = None


class JobApplicationUpdateByCandidateInput(BaseModel):
    application_number: str
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    civility: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    country_code: Optional[str] = None
    date_of_birth: Optional[date] = None
    attachments : Optional[List[JobAttachmentInput2]]
    email : EmailStr
    otp_code: str


class JobApplicationOTPRequestInput(BaseModel):
    application_number: str
    email: EmailStr


class JobAttachmentOut(BaseModel):
    id: int
    application_id: Optional[int]
    document_type: str
    file_path: str
    name: str  # Nom du fichier
    created_at: datetime
    updated_at: datetime
    
    @property
    def url(self) -> str:
        """URL complète du fichier (alias pour file_path)"""
        return self.file_path


class JobApplicationOut(BaseModel):
    id: int
    job_offer_id: str
    application_number: str
    status: str
    refusal_reason: Optional[str]
    submission_fee: float
    currency: str
    payment_id : Optional[str]
    email: str
    phone_number: str
    first_name: str
    last_name: str
    civility: Optional[str]
    country_code: Optional[str]
    city: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date]
    created_at: datetime
    updated_at: datetime

class JobApplicationFullOut(JobApplicationOut):
    attachments : Optional[List[JobAttachmentOut]]

class PaymentJobApplicationOut(BaseModel):
    job_application  : JobApplicationOut
    payment : Optional[InitPaymentOut] = None

class JobApplicationFilter(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    search: Optional[str] = None
    status: Optional[str] = None
    is_paid: Optional[bool] = None  # None means show all, True means paid only, False means unpaid only
    job_offer_id: Optional[str] = None
    order_by: Literal["created_at", "application_number", "status"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"


class JobOfferOutSuccess(BaseOutSuccess):
    data: JobOfferOut


class JobOffersPageOutSuccess(BaseOutPage):
    data: List[JobOfferOut]

class PaymentJobApplicationOutSuccess(BaseOutSuccess):
    data: PaymentJobApplicationOut

class JobApplicationOutSuccess(BaseOutSuccess):
    data: JobApplicationOut


class JobApplicationsPageOutSuccess(BaseOutPage):
    data: List[JobApplicationOut]


class JobAttachmentOutSuccess(BaseOutSuccess):
    data: JobApplicationFullOut


class JobAttachmentListOutSuccess(BaseOutSuccess):
    data: List[JobAttachmentOut]


class UpdateJobOfferStatusInput(BaseModel):
    application_id: int
    status: ApplicationStatusEnum
    reason : Optional[str] = None