import os
import sys
from typing import Annotated, List, Optional, Set
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from src.api.user.service import UserService
from src.helper.file_helper import FileHelper
from src.helper.schemas import BaseOutFail,ErrorMessage
from src.api.user.models import  User
import random
import string
import jwt
from datetime import datetime, timedelta, timezone
from src.config import settings

import  uuid
from cryptography.hazmat.primitives import serialization
from src.config import settings
from jwcrypto import jwk


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = HTTPBearer()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes= settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt




async def get_current_user_id(token: Annotated[HTTPAuthorizationCredentials, Depends(oauth2_scheme)] ):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=BaseOutFail(
                message=ErrorMessage.INVALID_TOKEN.description,
                error_code= ErrorMessage.INVALID_TOKEN.value
                
            ).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    
    except InvalidTokenError:
        raise credentials_exception

async def get_current_user(user_id: Annotated[str, Depends(get_current_user_id)],user_service:Annotated[UserService, Depends()] ):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=BaseOutFail(
                message=ErrorMessage.COULD_NOT_VALIDATE_CREDENTIALS.description,
                error_code= ErrorMessage.COULD_NOT_VALIDATE_CREDENTIALS.value
                
            ).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user =  await user_service.get_by_id(user_id= user_id)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not current_user.status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,  detail=BaseOutFail(
                message=ErrorMessage.USER_NOT_ACTIVE.description,
                error_code= ErrorMessage.USER_NOT_ACTIVE.value
                
            ).model_dump() )
    
    
    return current_user



def check_permissions(required_permissions: List[str]):
    """ Dependency to check if the user has required permissions. """
    async def permission_checker(current: Annotated[User, Depends(get_current_user)]  , user_service:Annotated[UserService, Depends()]):
        val = await user_service.has_all_permissions(user_id=current.id, permissions=required_permissions)
        if not val :
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=BaseOutFail(
                message=ErrorMessage.ACCESS_DENIED.description,
                error_code= ErrorMessage.ACCESS_DENIED.value
                
            ).model_dump())
        return current
    return permission_checker


def check_roles(required_roles: List[str]):
    """ Dependency to check if the user has required roles. """
    def permission_checker(current: User = Depends(get_current_user)):
        if not current.has_all_role(required_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=BaseOutFail(
                message=ErrorMessage.ACCESS_DENIED.description,
                error_code= ErrorMessage.ACCESS_DENIED.value
                
            ).model_dump())
        return current
    return permission_checker

def generate_random_code(length=5):
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9

    return ''.join(random.choice(characters) for _ in range(length)).upper()


def list_keys_in_s3():
    """List all keys in S3 for this environment."""
    prefix = f"private/{settings.ENV}/rsa/"
    
    resp = FileHelper.get_aws_list_objects_v2(prefix=prefix)
    if "Contents" not in resp:
        return []
    return [obj["Key"] for obj in resp["Contents"]]

def load_key_from_s3(key_name: str):
    """Load a key JSON from S3 and return JWK object."""
    obj = FileHelper.get_aws_object(key=key_name)
    return jwk.JWK.from_json(obj["Body"].read().decode("utf-8"))

def get_all_keys():
    """Return a dict of {kid: JWK} for this environment."""
    keys = {}
    for key_name in list_keys_in_s3():
        kid = os.path.splitext(os.path.basename(key_name))[0]
        keys[kid] = load_key_from_s3(key_name)
    return keys

def get_active_key():
    """Load the newest key as active key (last by timestamp)."""
    keys = list_keys_in_s3()
    if not keys:
        raise Exception("No keys found in S3!")
    keys.sort(reverse=True)  # newest last
    active_key_name = keys[0]
    kid = os.path.splitext(os.path.basename(active_key_name))[0]
    return kid, load_key_from_s3(active_key_name)


def make_access_token(sub: str, aud: str, scope: str, ttl=600):
    kid, active_key = get_active_key()
    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.JWK_ISS, "sub": sub, "aud": aud, "scope": scope,
        "iat": int(now.timestamp()), "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        payload,
        active_key.export_to_pem(private_key=True, password=None),
        algorithm=settings.JWK_ALGORITHM,
        headers={"kid": kid}
    )
    return token


def generate_kid():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{settings.ENV}-{settings.JWK_ALGORITHM}-{timestamp}"

async def rotate_key():
    
    kid = generate_kid()
    key = jwk.JWK.generate(kty="RSA", size=2048)

    key_json = key.export(private_key=True)
    s3_key = f"{settings.ENV}/rsa/{kid}.json"
    
    await FileHelper.upload_private_byte(key_json, location=f"{settings.ENV}/rsa/", name=kid, content_type="json")

    print(f"✅ New key created: {s3_key} with kid={kid}")
    




# In prod, use Redis/DB. This is a simple in-memory denylist for demo purposes.
_REVOKED_JTIS: Set[str] = set()

def revoke_jti(jti: str):
    _REVOKED_JTIS.add(jti)

def _ensure(required_scopes: Set[str], token_scopes: Set[str]):
    if required_scopes and not required_scopes.issubset(token_scopes):
        raise HTTPException(status_code=403, detail="insufficient_scope")

def require_oauth_client(required_scopes: Optional[Set[str]] = None, accepted_auds: Optional[Set[str]] = None):
    required_scopes = required_scopes or set()
    accepted_auds = accepted_auds or set()

    async def _dep(credentials = Depends(oauth2_scheme)):
        token = credentials.credentials
        try:
            # 1) Get KID and resolve key
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise HTTPException(status_code=401, detail="missing_kid")
            
            
            key_obj = get_all_keys()[kid]

            pub_pem = key_obj.export_to_pem(private_key=False, password=None) 

            payload = jwt.decode(
                token,
                pub_pem,
                algorithms=[settings.JWK_ALGORITHM],
                issuer=settings.JWK_ISS,
                options={"require": ["exp", "iat", "iss", "sub"]},
                audience="content-lafaom",
                leeway=5,
            )

            # 3) Basic custom checks
            if payload.get("typ") not in (None, "access"):  # if you set typ="access"
                raise HTTPException(status_code=401, detail="wrong_token_type")

            # 4) Revocation / replay defense
            jti = payload.get("jti")
            if jti and jti in _REVOKED_JTIS:
                raise HTTPException(status_code=401, detail="token_revoked")

            # 5) Scope
            token_scopes = set(payload.get("scope", "").split())
            _ensure(required_scopes, token_scopes)

            return payload  # pass claims to the route
        except HTTPException as e:
            print(e.with_traceback(sys.exc_info()[2]))
            raise
        except Exception as e:
            print(e.with_traceback(sys.exc_info()[2]))
            raise HTTPException(status_code=401, detail="invalid_or_expired_token")

    return _dep