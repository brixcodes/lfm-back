from pydantic import BaseModel, EmailStr,Field
from typing import List,Optional,Literal
from datetime import datetime
from src.helper.schemas import BaseOutSuccess, BaseOutPage
from src.api.system.models import OrganizationStatusEnum, OrganizationTypeEnum

# OrganizationCenter Input Schemas
class CreateOrganizationCenterInput(BaseModel):
    name: str
    address: str = ""
    city: str = ""
    postal_code: Optional[str] = None
    country_code: str = ""
    telephone_number: str = ""
    mobile_number: str = ""
    email: EmailStr 
    website: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: OrganizationStatusEnum = OrganizationStatusEnum.ACTIVE
    organization_type: OrganizationTypeEnum = OrganizationTypeEnum.MAIN
    description: Optional[str] = None

class UpdateOrganizationCenterInput(BaseModel):
    name: str
    address: str = ""
    city: str = ""
    postal_code: Optional[str] = None
    country_code: str = "SN"
    telephone_number: str = ""
    mobile_number: str = ""
    email: EmailStr 
    website: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: OrganizationStatusEnum
    organization_type: OrganizationTypeEnum
    description: Optional[str] = None

class UpdateOrganizationStatusInput(BaseModel):
    status: OrganizationStatusEnum

# OrganizationCenter Output Schemas
class OrganizationCenterOut(BaseModel):
    id: int
    name: str
    address: str
    city: str
    postal_code: Optional[str] = None
    country_code: str
    telephone_number: str
    mobile_number: str
    email: str
    website: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str
    organization_type: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Success Response Schemas
class OrganizationCenterOutSuccess(BaseOutSuccess):
    data: OrganizationCenterOut

class OrganizationCenterListOutSuccess(BaseOutSuccess):
    data: List[OrganizationCenterOut]

class OrganizationCentersPageOutSuccess(BaseOutPage):
    data: List[OrganizationCenterOut]

# Filter Schema
class OrganizationCenterFilter(BaseModel):
    page: int | None = Field(1, ge=1)
    page_size: int | None = Field(20, ge=1, le=100)
    search: Optional[str] = None
    status: Optional[OrganizationStatusEnum] = None
    organization_type: Optional[OrganizationTypeEnum] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    order_by: Literal["created_at", "updated_at", "name"] = "created_at"
    asc: Literal["asc", "desc"] = "asc"

# List Input Schema
class OrganizationCenterListInput(BaseModel):
    organization_center_ids: List[int]