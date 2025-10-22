from sqlmodel import   TIMESTAMP, Field,Relationship,SQLModel
from datetime import datetime
from src.helper.model import CustomBaseModel,CustomBaseUUIDModel
from typing import  Optional
from src.api.user.models import User



class RefreshToken(CustomBaseUUIDModel,table=True):
    __tablename__ = "refresh_token"
    token : str = Field(nullable=False)
    user_id : str = Field(nullable=False)
    expires_at: datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False) 

    
    
class ForgottenPAsswordCode(CustomBaseModel,table=True):
    __tablename__ = "forgotten_password_code"
    
    user_id: str  | None =  Field(default=None, foreign_key="users.id")
    email : str = Field(nullable=False)
    code : str = Field(nullable=False)
    end_time : datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False)
    active : bool = Field(default=True)



class ChangeEmailCode(CustomBaseModel,table=True):
    __tablename__ = "change_email_code"
    
    user_id: str  | None =  Field(default=None, foreign_key="users.id")
    email : str = Field(nullable=False)
    code : str = Field(nullable=False)
    end_time : datetime = Field(sa_type=TIMESTAMP(timezone=True), nullable=False)
    active : bool = Field(default=True)
    
    
    
    
class TwoFactorCode(CustomBaseModel,table=True):
    __tablename__ = "two_factor_code"
    
    user_id: str  | None =  Field(default=None, foreign_key="users.id")
    email : str = Field(nullable=False)
    code : str = Field(nullable=False)
    end_time : datetime 
    active : bool = Field(nullable=True,default=True)
    