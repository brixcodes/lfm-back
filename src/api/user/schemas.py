from pydantic import BaseModel,Field
from typing import List,Optional,Literal
from datetime import date, datetime
from src.api.user.models import CivilityEnum, UserStatusEnum, UserTypeEnum
from src.helper.schemas import BaseOutPage, BaseOutSuccess



class CreateUserInput(BaseModel):

    first_name: str 
    last_name: str 
    password: str
    birth_date: date | None = None
    civility : CivilityEnum | None = None
    country_code : str | None = "SN"
    mobile_number : str | None = None
    fix_number: str | None = None
    email: str | None 
    status : UserStatusEnum
    lang : Literal["en","fr"] = "en" 
    web_token : str | None 
    user_type : UserTypeEnum 
    two_factor_enabled : bool 
    
class UpdateStatusInput(BaseModel):
    status : UserStatusEnum

class UpdateUserInput(BaseModel):
    
    first_name: Optional[str] = None 
    last_name: Optional[str] = None 
    user_type: Optional[str] = None
    password: Optional[str] = None
    birth_date: date | None  = None
    civility : str | None = None
    country_code : str | None = None
    mobile_number : str | None = None
    fix_number: str | None = None
    email: str | None = None
    status : Optional[str] = None
    lang : Optional[str] = None 
    web_token : str | None 
    two_factor_enabled : Optional[bool] = None



class ListDataInput(BaseModel):

    data : List[int]
    



    
class UserOut(BaseModel):
    id : str
    first_name: str 
    last_name: str 
    country_code: str 
    phone_number: Optional[str] = None
    email: Optional[str] = None
    address : Optional[str] = None
    picture :  Optional[str] = None 
    status : str 
    lang : str 
    created_at : datetime
    updated_at : datetime
    prefer_notification : str 
    

class UserListInput(BaseModel):
    user_ids : List[str]


class ProfessionStatusOut(BaseModel):
    id : int
    professional_status : Optional[str] =""
    professional_experience_in_months : int  = 0
    socio_professional_category : Optional[str] ="" 
    job_position : Optional[str] ="" 
    employer : Optional[str] ="" 
    created_at : datetime

class AddressOut(BaseModel):
    id : int
    country_code: Optional[str]  =""
    city: Optional[str]  =""
    street: Optional[str]  =""
    postal_code: Optional[str] = "0000"
    state: Optional[str]  =""
    created_at : datetime

class UserSimpleOut(BaseModel):
    id : str
    first_name: str 
    last_name: str 
    birth_date: date | None 
    civility : str | None 
    country_code : str | None 
    mobile_number : str | None 
    fix_number: str | None 
    email: str | None 
    picture : str | None 
    status : str
    lang : str 
    web_token : str | None 
    last_login : datetime | None
    user_type : str 
    two_factor_enabled : bool 
    created_at : datetime
    
class SchoolCurriculumOut(BaseModel):
    id : int
    qualification : Optional[str] =""
    last_degree_obtained : Optional[str] =""
    date_of_last_degree :Optional[date] =""  
    created_at : datetime

class UserFullOut(UserSimpleOut):
    professions_status : Optional[ProfessionStatusOut]  
    addresses : List[AddressOut]
    school_curriculum : Optional[SchoolCurriculumOut] 
    

class UserOutSuccess(BaseOutSuccess):
    
    data: UserSimpleOut 

class UserFullOutSuccess(BaseOutSuccess):
    
    data: UserFullOut 

    
class UserListOutSuccess(BaseOutSuccess):
    
    data: List [UserSimpleOut]  
    
class UsersPageOutSuccess(BaseOutPage):
    
    data: List [UserSimpleOut]

class UserFilter(BaseModel):
    page: int | None = Field(1, ge=1)
    page_size: int | None = Field(20, ge=20)
    search : Optional[str] = None
    user_type :  Optional[UserTypeEnum] = None
    country_code : Optional[str] = None
    
    order_by:  Literal["created_at", "last_login","first_name","last_name"] = "created_at"
    asc :  Literal["asc", "desc"] = "asc"
    
class AssignPermissionsInput(BaseModel):
    user_id : str
    permissions : List[str]
    
class AssignRoleInput(BaseModel):
    user_id : str
    role_id : int
    
class RoleOut(BaseModel):
    id : int
    name : str
    description : Optional[str] = ''
    
class RoleOutSuccess(BaseOutSuccess):
    data : RoleOut
    
class RoleListOutSuccess(BaseOutSuccess):
    data : List[RoleOut]    
    
class PermissionOut(BaseModel):
    user_id : str | None
    role_id : int | None
    permission : str

class PermissionOutSuccess(BaseOutSuccess):
    data : PermissionOut
    
class PermissionListOutSuccess(BaseOutSuccess):
    data : List[PermissionOut]
    
    
class PermissionSmallListOutSuccess(BaseOutSuccess):
    data : List[str]