from fastapi import Depends
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session_async
from src.api.auth.models import RefreshToken,ForgottenPAsswordCode,ChangeEmailCode, TwoFactorCode


from sqlmodel import select, delete
from datetime import timedelta,datetime,timezone
from passlib.context import CryptContext
from src.api.auth.utils import get_password_hash
from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    async def generate_refresh_token(self, user_id:str,expires_delta: timedelta | None = None  ):
        
        expires_at = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=3600))
        token = secrets.token_urlsafe(112)  # Generate a random token
            
        # Check if the token already exists in the database
        
        existing_token = await self.get_by_token(token)
        if existing_token is None:
            # If not, store it and return
            new_access_token = RefreshToken(token=  get_password_hash(token) , user_id=user_id,expires_at = expires_at)
            await self.session.merge(new_access_token)
            await self.session.commit()
            return new_access_token ,token

    

    async def get_by_token(self, id: str):
        statement = select(RefreshToken).where(RefreshToken.id == id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_token_valid(self, token: str):
        statement = select(RefreshToken).where(RefreshToken.token == token).where(RefreshToken.expires_at >= datetime.now(timezone.utc))
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def delete(self, token: str):
        statement = delete(RefreshToken).where(RefreshToken.token == token)
        await self.session.execute(statement)
        await self.session.commit()

    async def get_forgotten_password_code(self, email:str,code:str  ):
        
        statement = select(ForgottenPAsswordCode).where(ForgottenPAsswordCode.email == email).where(ForgottenPAsswordCode.code == code)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    
    async def get_change_email_code(self, email:str,code:str , user_id : str ) -> ChangeEmailCode  | None:
        
        statement = select(ChangeEmailCode).where(ChangeEmailCode.email == email).where(ChangeEmailCode.code == code).where(ChangeEmailCode.user_id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def save_change_email_code(self,user_id :str ,  email : str, code : str   ):
        
        code = ChangeEmailCode(email=email,code=code,user_id=user_id,end_time=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_CODE_EXPIRE_MINUTES))
        await self.session.merge(code)
        await self.session.commit()
        return code
    
    async def save_forgotten_password_code(self,user_id :str , email : str, code : str  ):
        
        code = ForgottenPAsswordCode(user_id=user_id,email=email,code=code,end_time=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_CODE_EXPIRE_MINUTES))
        await self.session.merge(code)
        await self.session.commit()
        return code
    
    
    async def make_forgotten_password_used(self, id : int  ):
        
        statement = select(ForgottenPAsswordCode).where(ForgottenPAsswordCode.id == id)
        result = await self.session.execute(statement)
        code = result.scalar_one_or_none()
        code.active = False
        await self.session.commit()
        
        
        return code
        
    async def make_change_email_used(self, id : int  ):
        
        statement = select(ChangeEmailCode).where(ChangeEmailCode.id == id)
        result = await self.session.execute(statement)
        code = result.scalar_one_or_none()
        code.active = False
        await self.session.commit()
        
        return code
    
    

    async def save_two_factor_code(self, code : str, user_id : str, email : str  ):
        statement = select(TwoFactorCode).where(TwoFactorCode.user_id == user_id).where(TwoFactorCode.active == True).order_by(TwoFactorCode.id.desc())
        old_code_result = await self.session.execute(statement)
        old_code = old_code_result.scalar_one_or_none()
        if old_code != None :
            old_code.active = False
            self.session.add(old_code)
            self.session.commit()

        code = TwoFactorCode(code=code,user_id=user_id,email=email,end_time=datetime.now(timezone.utc) + timedelta(minutes=30))
        self.session.add(code)
        self.session.commit()
        self.session.refresh(code)
        return code
    
    async def get_two_factor_code(self,  code : str, email : str  ):
        
        statement = select(TwoFactorCode).where(TwoFactorCode.email == email).where(TwoFactorCode.code == code).order_by(TwoFactorCode.id.desc())
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def make_two_factor_code_used(self, id : int  ):
        
        statement = select(TwoFactorCode).where(TwoFactorCode.id == id)
        result = await self.session.execute(statement)
        code = result.scalar_one_or_none()
        code.active = False
        self.session.add(code)
        self.session.commit()
        self.session.refresh(code)
        
        return code
