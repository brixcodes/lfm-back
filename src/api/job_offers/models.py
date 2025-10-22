
from sqlmodel import  Field,Relationship
from datetime import date
from src.helper.model import CustomBaseUUIDModel,CustomBaseModel
from typing import List, Optional
from enum import Enum
from  datetime import datetime
from sqlalchemy import Column, Numeric, JSON, TIMESTAMP



class ApplicationStatusEnum(str, Enum):
    RECEIVED = "RECEIVED"
    REFUSED = "REFUSED"
    APPROVED = "APPROVED"
class JobOffer(CustomBaseUUIDModel, table=True):
    __tablename__ = "job_offers"
    
    # Informations générales
    reference: str = Field(index=True, description="Référence de l'offre")
    title: str = Field(description="Titre du poste")
    location: str = Field(description="Ville ou localisation")
    postal_code: str = Field(description="Code postal")
    contract_type: str = Field(description="Type de contrat (ex: CDD, CDI)")
    uncertain_term: bool = Field(default=False, description="Contrat à terme incertain")
    start_date: Optional[date] = Field(default=None, description="Date souhaitée de prise de poste")
    end_date: Optional[date] = Field(default=None, description="Date de fin du contrat")
    weekly_hours: Optional[int] = Field(default=None, description="Temps de travail hebdomadaire en heures")
    driving_license_required: bool = Field(default=False, description="Permis requis")
    submission_deadline: date = Field(default=None, description="Dernière date de soumission")

    # Missions et responsabilités (texte libre)
    main_mission: Optional[str] = Field(default=None, description="Mission principale du poste")
    responsibilities: Optional[str] = Field(default=None, description="Responsabilités clés")
    competencies: Optional[str] = Field(default=None, description="Compétences requises")
    profile: Optional[str] = Field(default=None, description="Profil recherché")

    # Salaire et avantages
    salary: Optional[float] = Field(default=None, description="Salaire brut mensuel en euros")
    benefits: Optional[str] = Field(default=None, description="Avantages proposés")
    
    
    submission_fee: Optional[float] = Field(
        default=None,
        sa_column=Column(Numeric(precision=12, scale=2))
    )
    currency : str = Field(default="EUR")
    
    attachment: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON)
    )

    # Conditions d’exercice
    conditions: Optional[str] = Field(default=None, description="Conditions de travail et règles associatives")

class JobApplication(CustomBaseModel, table=True):
    __tablename__ = "job_applications"

    job_offer_id: str = Field(foreign_key="job_offers.id")
    application_number: str = Field(default=None, max_length=50, index=True, unique=True)
    status: ApplicationStatusEnum = Field(default=ApplicationStatusEnum.RECEIVED)
    refusal_reason: Optional[str] = Field(default=None)
    submission_fee: float = Field(
        default=None,
        sa_column=Column(Numeric(precision=12, scale=2))
    )
    currency : Optional[str] = Field(default="EUR",nullable=True)
    email : str 
    phone_number : str
    first_name : str
    last_name : str
    civility : str | None = Field(nullable=True)
    city : str | None = Field(nullable=True)
    address : str | None = Field(nullable=True)
    country_code : str | None = Field(nullable=True)
    date_of_birth : Optional[date] = Field(nullable=True)
    payment_id : Optional[str] = Field(default=None,foreign_key="payments.id", nullable=True)
    job_offer: JobOffer = Relationship()
    
    attachments: List["JobAttachment"] = Relationship( sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class JobAttachment(CustomBaseModel, table=True):
    __tablename__ = "job_attachments"

    application_id: Optional[int] = Field(foreign_key="job_applications.id", nullable=True)
    document_type: str = Field( max_length=100)
    file_path: str = Field(max_length=255)
    name: str = Field(max_length=255, description="Nom du fichier")


class JobApplicationCode(CustomBaseModel, table=True):
    __tablename__ = "job_application_codes"
    
    application_id: int = Field(foreign_key="job_applications.id", nullable=False)
    email: str = Field(nullable=False)
    code: str = Field(nullable=False)
    end_time: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    active: bool = Field(default=True)

