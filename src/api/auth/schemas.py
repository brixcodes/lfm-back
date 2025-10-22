from typing import  Literal, Optional
from pydantic import BaseModel,EmailStr
import phonenumbers
from  datetime import date, datetime
from src.api.user.schemas import UserFullOut, UserOut



class Token(BaseModel):
    token: str
    token_type: str
    refresh_token: str =""
    device_id: str = ""
    expires_in: int | None = None

class UserTokenOut(BaseModel):
    access_token : Token
    user : UserFullOut 

class TokenData(BaseModel):
    token : str | None = None
    user_id : str | None = None
    expire_at: datetime | None = None
    
class LoginInput(BaseModel):
    email : EmailStr
    password : str = ""
    
class UpdatePasswordInput(BaseModel):
    password: str 
    new_password : str 
    

class AuthCodeInput(BaseModel):
    code : str 


class UpdateDeviceInput(BaseModel):
    device_id : str

        
class PhoneUtil():
    def __init__(self,number:str,country:str = None) -> None:
        try :
            self._value = phonenumbers.parse(number,country)
            print(self._value)
        except :   
            self._value = None 
            
    
    def isValid(self)-> bool:
        if self._value == None:
            return False
        else :    
            return phonenumbers.is_valid_number(self._value) 
        

class ChangeEmailInput(BaseModel) : 
    
    email : EmailStr
    password : str = ""
    
    
class ValidateChangeCodeInput(BaseModel) : 
    email : EmailStr
    code : str
    
class ValidateForgottenCodeInput(BaseModel) : 
    email : EmailStr
    code : str
    password : str

class ForgottenPasswordInput(BaseModel):
    email : EmailStr
    
class RefreshTokenInput(BaseModel) : 
    refresh_token : str
    device_id: str = ""


class SocialTokenInput(BaseModel) : 
    token : str
    platform : Literal["ios", "android", "web"] = "web"


class UpdateUserProfile(BaseModel) : 

    first_name: str 
    last_name: str 
    user_type: str
    status: str
    birth_date: date 
    civility : str 
    country_code : str ="SN"
    mobile_number : str 
    fix_number: str 
    two_factor_enabled : bool = False
    lang : str = "fr"
    
class UpdateCurriculumInput(BaseModel):

    qualification : Optional[str] =""
    last_degree_obtained : Optional[str] =""
    date_of_last_degree :Optional[date] =""  

class UpdateProfessionStatusInput(BaseModel):

    professional_status : Optional[str] =""
    professional_experience_in_months : int  = 0
    socio_professional_category : Optional[str] ="" 
    job_position : Optional[str] ="" 
    employer : Optional[str] ="" 
    
class UpdateAddressInput(BaseModel):

    primary_address_country_code: Optional[str]  =""
    primary_address_city: Optional[str]  =""
    primary_address_street: Optional[str]  =""
    primary_address_postal_code: Optional[str] = "0000"
    primary_address_state: Optional[str]  =""
    
    billing_address_country_code: Optional[str]  =""
    billing_address_city: Optional[str]  =""
    billing_address_street: Optional[str]  =""
    billing_address_postal_code: Optional[str] = "0000"
    billing_address_state: Optional[str]  =""


class ClientACcessTokenInput(BaseModel) : 
    grant_type: str
    client_id: str
    client_secret: str
    audience: str
    scope: str = ""