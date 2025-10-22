from sqlmodel import Field, Relationship
from datetime import datetime
from src.helper.model import CustomBaseUUIDModel
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from sqlalchemy import TIMESTAMP, Column, Numeric, Boolean

if TYPE_CHECKING:
    from src.api.user.models import User

class CabinetApplicationStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class CabinetApplication(CustomBaseUUIDModel, table=True):
    __tablename__ = "cabinet_applications"
    
    # Informations de l'entreprise
    company_name: str = Field(max_length=255, nullable=False)
    contact_email: str = Field(max_length=255, nullable=False, unique=True)
    contact_phone: str = Field(max_length=50, nullable=False)
    address: str = Field(nullable=False)
    registration_number: str = Field(max_length=100, nullable=False)
    
    # Expérience et qualifications
    experience_years: int = Field(nullable=False)
    qualifications: Optional[str] = Field(default=None)
    
    # Documents
    proposal_document_path: Optional[str] = Field(default=None, max_length=500)
    technical_proposal: Optional[str] = Field(default=None)
    financial_proposal: Optional[str] = Field(default=None)
    references: Optional[str] = Field(default=None)
    
    # Statut de la candidature
    status: CabinetApplicationStatus = Field(default=CabinetApplicationStatus.PENDING)
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    
    # Informations de paiement
    payment_reference: Optional[str] = Field(default=None, max_length=100)
    payment_id: Optional[str] = Field(default=None, foreign_key="payments.id", nullable=True)
    payment_amount: float = Field(default=50.0)
    payment_currency: str = Field(default="EUR", max_length=3)
    payment_date: Optional[datetime] = Field(default=None)
    
    # Compte utilisateur créé
    user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    account_created: bool = Field(default=False)
    credentials_sent: bool = Field(default=False)
    
    # Campaign reference
    campaign_id: Optional[str] = Field(default=None, foreign_key="cabinet_recruitment_campaigns.id")
    
    # Relations
    user: Optional["User"] = Relationship(back_populates="cabinet_application")
    campaign: Optional["CabinetRecruitmentCampaign"] = Relationship(
        back_populates="applications",
        sa_relationship_kwargs={"primaryjoin": "CabinetApplication.campaign_id == CabinetRecruitmentCampaign.id"}
    )

class ApplicationFee(CustomBaseUUIDModel, table=True):
    __tablename__ = "application_fees"
    
    # Informations des frais
    amount: float = Field(nullable=False)
    currency: str = Field(default="EUR", max_length=3)
    description: str = Field(nullable=False)
    
    # Statut
    is_active: bool = Field(default=True)

class CabinetRecruitmentCampaign(CustomBaseUUIDModel, table=True):
    __tablename__ = "cabinet_recruitment_campaigns"
    
    # Informations de la campagne
    title: str = Field(max_length=255, nullable=False)
    description: str = Field(nullable=False)
    
    # Dates importantes
    start_date: datetime = Field(nullable=False)
    end_date: datetime = Field(nullable=False)
    
    # Frais de candidature
    application_fee_id: str = Field(foreign_key="application_fees.id")
    
    # Statut
    is_active: bool = Field(default=True)
    
    # Relations
    applications: List["CabinetApplication"] = Relationship(
        back_populates="campaign",
        sa_relationship_kwargs={"primaryjoin": "CabinetRecruitmentCampaign.id == CabinetApplication.campaign_id"}
    )
    application_fee: "ApplicationFee" = Relationship(
        sa_relationship_kwargs={"primaryjoin": "CabinetRecruitmentCampaign.application_fee_id == ApplicationFee.id"}
    )