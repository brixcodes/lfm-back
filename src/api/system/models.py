from sqlmodel import  Field
from src.helper.model import CustomBaseModel
from typing import  Optional
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import  TIMESTAMP, event

class OrganizationStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"

class OrganizationTypeEnum(str, Enum):
    MAIN = "main"
    BRANCH = "branch"
    PARTNER = "partner"
    AFFILIATE = "affiliate"

class OrganizationCenter(CustomBaseModel, table=True):
    __tablename__ = "organization_centers"

    name: str = Field(max_length=255, index=True, unique=True)
    address: str = Field(default="", max_length=255)
    city: str = Field(default='', max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=50)
    country_code: str = Field(default='', max_length=4)
    telephone_number: str = Field(default="", max_length=20)
    mobile_number: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=255)
    website: Optional[str] = Field(default=None, max_length=255)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    status: str = Field(default=OrganizationStatusEnum.ACTIVE, max_length=50)
    organization_type: str = Field(default=OrganizationTypeEnum.MAIN, max_length=50)
    description: Optional[str] = Field(default=None, max_length=5000)

def update_updated_at_organization(mapper, connection, target):
    target.updated_at = datetime.now(timezone.utc)

# Add the event listener for before update
event.listen(OrganizationCenter, 'before_update', update_updated_at_organization)
    