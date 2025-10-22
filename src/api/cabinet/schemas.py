from typing import Optional, List
from datetime import datetime
from pydantic import EmailStr, BaseModel, Field

from .models import CabinetApplicationStatus, PaymentStatus

class CabinetApplicationBase(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255, description="Nom de l'entreprise")
    contact_email: EmailStr = Field(..., description="Email de contact")
    contact_phone: str = Field(..., min_length=8, max_length=50, description="Téléphone de contact")
    address: str = Field(..., min_length=10, description="Adresse complète")
    registration_number: str = Field(..., min_length=5, max_length=100, description="Numéro d'enregistrement")
    experience_years: int = Field(..., ge=0, le=50, description="Années d'expérience")
    qualifications: Optional[str] = Field(None, description="Qualifications et certifications")
    technical_proposal: Optional[str] = Field(None, description="Proposition technique")
    financial_proposal: Optional[str] = Field(None, description="Proposition financière")
    references: Optional[str] = Field(None, description="Références clients")

class CabinetApplicationCreate(CabinetApplicationBase):
    pass

class CabinetApplicationUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_phone: Optional[str] = Field(None, min_length=8, max_length=50)
    address: Optional[str] = Field(None, min_length=10)
    qualifications: Optional[str] = None
    technical_proposal: Optional[str] = None
    financial_proposal: Optional[str] = None
    references: Optional[str] = None

class CabinetApplicationOut(CabinetApplicationBase):
    id: str
    status: CabinetApplicationStatus
    payment_status: PaymentStatus
    payment_reference: Optional[str]
    payment_amount: float
    payment_currency: str
    payment_date: Optional[datetime]
    account_created: bool
    credentials_sent: bool
    created_at: datetime
    updated_at: datetime
    # Informations de paiement (ajoutées dynamiquement)
    payment_url: Optional[str] = None

class CabinetApplicationPaymentInit(BaseModel):
    application_id: str
    amount: float = Field(50.0, description="Montant des frais de candidature")
    currency: str = Field("EUR", description="Devise")
    description: str = Field("Frais de candidature cabinet LAFAOM", description="Description du paiement")

class CabinetApplicationPaymentResponse(BaseModel):
    application_id: str
    payment_url: str = Field(..., description="URL de paiement CinetPay")
    payment_reference: str = Field(..., description="Référence de paiement")
    amount: float
    currency: str
    expires_at: datetime = Field(..., description="Date d'expiration du paiement")

class PaymentWebhookData(BaseModel):
    transaction_id: str
    status: str
    amount: float
    currency: str
    customer_email: str
    customer_name: str
    payment_reference: str

class CabinetApplicationCredentials(BaseModel):
    email: str
    username: str
    temporary_password: str
    login_url: str

class ApplicationFeeBase(BaseModel):
    amount: float = Field(..., gt=0, description="Montant des frais")
    currency: str = Field("EUR", description="Devise")
    description: str = Field(..., min_length=10, description="Description des frais")

class ApplicationFeeCreate(ApplicationFeeBase):
    pass

class ApplicationFeeUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    description: Optional[str] = Field(None, min_length=10)
    is_active: Optional[bool] = None

class ApplicationFeeOut(ApplicationFeeBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class CabinetRecruitmentCampaignBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255, description="Titre de la campagne")
    description: str = Field(..., min_length=20, description="Description de la campagne")
    start_date: datetime = Field(..., description="Date de début")
    end_date: datetime = Field(..., description="Date de fin")
    application_fee_id: str = Field(..., description="ID des frais de candidature")

class CabinetRecruitmentCampaignCreate(CabinetRecruitmentCampaignBase):
    pass

class CabinetRecruitmentCampaignUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    application_fee_id: Optional[str] = None
    is_active: Optional[bool] = None

class CabinetRecruitmentCampaignOut(CabinetRecruitmentCampaignBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    application_fee: ApplicationFeeOut

class CabinetApplicationStats(BaseModel):
    total_applications: int
    pending_applications: int
    paid_applications: int
    approved_applications: int
    rejected_applications: int
    total_revenue: float
    currency: str = "EUR"
