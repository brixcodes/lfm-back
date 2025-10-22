from typing import Annotated
from fastapi import Depends , HTTPException, status, APIRouter,UploadFile,File,Request,Response
from src.api.user.models import  User
from src.api.auth.schemas import ( ChangeEmailInput, ClientACcessTokenInput, ForgottenPasswordInput, Token,LoginInput, UpdateAddressInput, UpdateDeviceInput,
                                RefreshTokenInput, UpdateUserProfile,UserTokenOut,UpdatePasswordInput,AuthCodeInput, ValidateChangeCodeInput, ValidateForgottenCodeInput)

from src.api.auth.utils import (get_all_keys, get_current_active_user, make_access_token,verify_password,
                                generate_random_code,create_access_token)
from src.helper.file_helper import FileHelper
from src.helper.notifications import (ChangeAccountNotification,ForgottenPasswordNotification, LoginAlertNotification, TwoFactorAuthNotification)
from src.config import settings
from src.api.user.service import UserService
from src.api.auth.service import AuthService
from src.api.user.schemas import  PermissionListOutSuccess, RoleOutSuccess, UserFullOutSuccess, UserOutSuccess
from src.helper.schemas import ErrorMessage,BaseOutFail,BaseOutSuccess
from datetime import datetime, timezone
import re



router = APIRouter()


@router.post("/token", response_model=UserTokenOut | BaseOutSuccess)
async def login_for_access_token( request: Request,
    form_data: LoginInput, user_service: UserService = Depends(), token_service: AuthService = Depends()
) -> UserTokenOut | BaseOutSuccess:
    user = await user_service.get_full_by_email(form_data.email)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=BaseOutFail(
                message=ErrorMessage.INCORRECT_EMAIL_OR_PASSWORD.description,
                error_code=ErrorMessage.INCORRECT_EMAIL_OR_PASSWORD.value
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if user.two_factor_enabled:
        code = generate_random_code()
        token_service.save_two_factor_code(user_id=user.id, email=form_data.email, code=code)
        TwoFactorAuthNotification(
            email=user.email,
            code=code,
            time=30
        ).send_notification()
        return BaseOutSuccess(
            message="Code sent to your preferred notification channel successfully",
            success=True,
            data={"two_factor_enabled": True, "email": form_data.email}
        ).model_dump()

    refresh_token, token = await token_service.generate_refresh_token(user_id=user.id)
    access_token = create_access_token(data={"sub": user.id})
    
    await user_service.update_last_login(user_id=user.id)
    

    return {
        "access_token": Token(
            token=access_token, token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=token, device_id=refresh_token.id
        ),
        "user": user
    }

@router.post("/two-factor-token", response_model=UserTokenOut)
async def two_factor_token(response: Response,request: Request,
    form_data: ValidateChangeCodeInput, user_service: UserService = Depends(), token_service: AuthService = Depends()
) -> UserTokenOut:

    code = await token_service.get_two_factor_code(email=form_data.email,code=form_data.code)   
    
    if  code == None :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.EMAIL_NOT_FOUND.description,
                    error_code= ErrorMessage.EMAIL_NOT_FOUND.value
                ).model_dump()
        )
    if not code.active  : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.CODE_ALREADY_USED.description,
                    error_code= ErrorMessage.CODE_ALREADY_USED.value
                ).model_dump()
        )
    if code.end_time.tzinfo is None:
        code.end_time = code.end_time.replace(tzinfo=timezone.utc)           
    if code.end_time <= datetime.now(timezone.utc)  : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.CODE_HAS_EXPIRED.description,
                    error_code= ErrorMessage.CODE_HAS_EXPIRED.value
                ).model_dump()
        )
    user = await user_service.get_full_by_id(user_id=code.user_id)
    
    
    refresh_token, token = await token_service.generate_refresh_token(user_id=user.id)
    
    access_token = create_access_token(data={"sub": user.id})
    await token_service.make_two_factor_code_used(id=code.id)

    return {
            "access_token" : Token(
                token=access_token, token_type="bearer", expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,refresh_token= token,device_id=refresh_token.id
            ),
            "user" :user
        }


@router.post("/refresh-token", response_model=UserTokenOut)
async def get_token_from_refresh_token(request: Request,
    form_data: RefreshTokenInput, user_service: UserService = Depends(), token_service: AuthService = Depends()
) -> UserTokenOut:
    
    token = await token_service.get_by_token(id=form_data.device_id)   

    if token is None or not verify_password(form_data.refresh_token,token.token  ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=BaseOutFail(
                message=ErrorMessage.REFRESH_TOKEN_NOT_FOUND.description,
                error_code=ErrorMessage.REFRESH_TOKEN_NOT_FOUND.value,
            ).model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )    
    
    if token.expires_at.tzinfo is None:
        token.expires_at = token.expires_at.replace(tzinfo=timezone.utc)    
    
    if token.expires_at <= datetime.now(timezone.utc)  : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.REFRESH_TOKEN_HAS_EXPIRED.description,
                    error_code= ErrorMessage.REFRESH_TOKEN_HAS_EXPIRED.value
                ).model_dump()
        )


    user = await user_service.get_full_by_id(user_id=token.user_id )
    
    access_token = create_access_token(
        data={"sub": user.id})
    

    
    return {
            "access_token" : Token(
                token=access_token, token_type="bearer", expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,refresh_token= form_data.refresh_token,device_id = form_data.device_id  
            ),
            "user" : user
        }


@router.post("/password-forgotten")
async def password_forgotten(
    input: ForgottenPasswordInput,  token_service : Annotated[AuthService, Depends()], user_service : Annotated[UserService , Depends()],
):

        
    user =await user_service.get_by_email(user_email=input.email)   
    
    
    if user == None:
        return {
            "message": "Save successfully",
            "data" : {
                "email" :input.email
            },
            "success": True
        }
    
    code = generate_random_code()  

    save_code  = await token_service.save_forgotten_password_code(user_id=user.id,email=input.email,code=code)
    
    ForgottenPasswordNotification(
            email=user.email,
            code=code,
            time = 30,
            
        ).send_notification()
    
    
    
    return {
            "message": "Save successfully",
            "data" : {
                "email" :input.email
            },
            "success": True
        }


@router.post("/validate-password-forgotten-code",response_model=UserTokenOut)
async def validate_forgotten_password_code(response: Response,
    validate_input: ValidateForgottenCodeInput, user_service : Annotated[UserService , Depends()], token_service : Annotated[AuthService, Depends()]
):

    code = await token_service.get_forgotten_password_code(email=validate_input.email,code=validate_input.code)   
    
    if  code == None :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.EMAIL_NOT_FOUND.description,
                    error_code= ErrorMessage.EMAIL_NOT_FOUND.value
                ).model_dump()
        )
        
    if not code.active  : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.CODE_ALREADY_USED.description,
                    error_code= ErrorMessage.CODE_ALREADY_USED.value
                ).model_dump()
        )
        
    if code.end_time.tzinfo is None:
        code.end_time = code.end_time.replace(tzinfo=timezone.utc)           
    if code.end_time <= datetime.now(timezone.utc)  : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.CODE_HAS_EXPIRED.description,
                    error_code= ErrorMessage.CODE_HAS_EXPIRED.value
                ).model_dump()
        )
        
    
    
    user = await user_service.update_password( user_id= code.user_id,password= validate_input.password )
    await token_service.make_forgotten_password_used(id=code.id)
    
    refresh_token, token = await token_service.generate_refresh_token(user_id=user.id)
    
    
    access_token = create_access_token(
        data={"sub": user.id})
    user = await user_service.get_full_by_id(user_id=user.id)

    return {
            "access_token" : Token(
                token=access_token, token_type="bearer", expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,refresh_token= token,device_id=refresh_token.id
            ),
            "user" : user
        }


@router.post("/change-email")
async def change_email(
    current_user: Annotated[User, Depends(get_current_active_user)],input: ChangeEmailInput, user_service : Annotated[UserService , Depends()], token_service : Annotated[AuthService, Depends()]
):

    if not verify_password(input.password  , current_user.password) :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.PASSWORD_NOT_CORRECT.description,
                    error_code= ErrorMessage.PASSWORD_NOT_CORRECT.value
                ).model_dump()
        )
    
    user_by_email = await user_service.get_by_email(input.email)

    if user_by_email :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.EMAIL_ALREADY_TAKEN.description,
                    error_code= ErrorMessage.EMAIL_ALREADY_TAKEN.value
                ).model_dump()
        )
        
    
    
    code = generate_random_code()  

    save_code  = await token_service.save_change_email_code(user_id=current_user.id,email=input.email,code=code)
    
    
    ChangeAccountNotification(
            
            email=input.email,
            code=code,
            time = 30,
            lang=current_user.lang
            
        ).send_notification()  
    

    return {
            "message": "Save successfully",
            "data" : {
                "email" :input.email
            },
            "success": True
        }


@router.post("/validate-change-email-code", response_model=UserFullOutSuccess)
async def validate_change_email_code(
    current_user: Annotated[User, Depends(get_current_active_user)],validate_input: ValidateChangeCodeInput, user_service : Annotated[UserService , Depends()], token_service : Annotated[AuthService, Depends()]
):

    code = await token_service.get_change_email_code(email=validate_input.email,code=validate_input.code,user_id =current_user.id)   
    
    if  code == None :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.EMAIL_NOT_FOUND.description,
                    error_code= ErrorMessage.EMAIL_NOT_FOUND.value
                ).model_dump()
        )
    if not code.active  : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.CODE_ALREADY_USED.description,
                    error_code= ErrorMessage.CODE_ALREADY_USED.value
                ).model_dump()
        )
    if code.end_time.tzinfo is None:
        code.end_time = code.end_time.replace(tzinfo=timezone.utc)           
    if code.end_time <= datetime.now(timezone.utc)  : 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.CODE_HAS_EXPIRED.description,
                    error_code= ErrorMessage.CODE_HAS_EXPIRED.value
                ).model_dump()
        )

    user = await user_service.update_phone_or_email( user_id= code.user_id,email=code.email  )
    await token_service.make_change_email_used(id=code.id)
    user = await user_service.get_full_by_id(user_id=current_user.id)
    
    return {
        "data" : user,
        "message" : "email change successfully"
    }

@router.get("/me", response_model=UserFullOutSuccess)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_service : Annotated[UserService , Depends()],
):
    full_user = await user_service.get_full_by_id(user_id=current_user.id)
    return {
        "data":full_user,
        "message" : "profile fetch successfully"
    }


@router.get('/my-permissions',response_model=PermissionListOutSuccess,tags=["Auth"])
async def get_user_permissions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_service: UserService = Depends()
):
    
    user_permissions = await user_service.get_all_user_permissions(user_id=current_user.id)
    
    return  { "message" : "My Permissions", "data" : user_permissions }


@router.get('/my-role',response_model=RoleOutSuccess,tags=["Auth"])
async def get_user_role(
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_service: UserService = Depends()
):
    
    user_role = await user_service.get_user_role(user_id=current_user.id)
    
    if len(user_role) == 0  :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.ROLE_NOT_FOUND.description,
                    error_code= ErrorMessage.ROLE_NOT_FOUND.value
                ).model_dump()
        )
    
    return  { "message" : "My Role", "data" : user_role[0] }

@router.post("/update-profile",response_model=UserFullOutSuccess)
async def update_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],update_input: UpdateUserProfile, user_service : Annotated[UserService , Depends()]
):
    user = await user_service.update_profile( user_id= current_user.id,input=update_input  )
    user = await user_service.get_full_by_id(user_id=current_user.id)
    return {
        "data":user,
        "message" : "profile updated successfully"
    }

@router.post("/update-addresses",response_model=UserFullOutSuccess)
async def update_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],update_input: UpdateAddressInput, user_service : Annotated[UserService , Depends()]
):
    primary_address,secondary_address = await user_service.update_address( user_id= current_user.id,input=update_input  )
    
    user = await user_service.get_full_by_id(user_id=current_user.id)
    
    return {
        "data":user,
        "message" : "profile updated successfully"
    }

@router.post("/update-web-id",response_model=UserFullOutSuccess)
async def update_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],input: UpdateDeviceInput, user_service : Annotated[UserService , Depends()]
):
    user = await user_service.update_device_id( user_id= current_user.id, input=input )
    user = await user_service.get_full_by_id(user_id=current_user.id)
    return {
        "data":user,
        "message" : "Web device ID updated successfully"
    }
    

@router.post("/update-password",response_model=UserFullOutSuccess)
async def update_password(
    current_user: Annotated[User, Depends(get_current_active_user)],update_input: UpdatePasswordInput, user_service : Annotated[UserService , Depends()]
):
    if not verify_password(update_input.password  , current_user.password) :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.PASSWORD_NOT_CORRECT.description,
                    error_code= ErrorMessage.PASSWORD_NOT_CORRECT.value
                ).model_dump()
        )
    
    user = await user_service.update_password( user_id= current_user.id,password=update_input.new_password  )
    user = await user_service.get_full_by_id(user_id=current_user.id)
    return {
        "data":user,
        "message" : "password change successfully"
    }



@router.post("/upload-profile-image",response_model=UserFullOutSuccess)
async def update_profile_image(
    current_user: Annotated[User, Depends(get_current_active_user)],image: Annotated[UploadFile, File()], user_service : Annotated[UserService , Depends()]
):
    name = f"{current_user.first_name}_{current_user.last_name}_profile"
    try :
        document , _ , _ = await FileHelper.upload_file(file=image,location="/profile", name = name)
        FileHelper.delete_file(current_user.picture)
    
    except Exception as e :
        print("Error when uploading profile image :" ,e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.UNKNOWN_ERROR.description,
                    error_code= ErrorMessage.UNKNOWN_ERROR.value
                ).model_dump()
        )


    user = await user_service.update_profile_image( user_id= current_user.id,picture= document   )
    user = await user_service.get_full_by_id(user_id=current_user.id)
    return {
        "data":user,
        "message" : "picture image updated successfully"
    }



@router.post("/oauth/token")
async def get_client_access_token(input : ClientACcessTokenInput):
    # TODO: authenticate client_id/client_secret and check allowed scopes/audience
    access_token = make_access_token(sub=f"svc:{input.client_id}", aud=input.audience, scope=input.scope)
    return {"access_token": access_token, "token_type": "Bearer", "expires_in": 600}


@router.get("/jwks.json")
async def jwks():
    all_keys = get_all_keys()
    jwks = []
    for kid, key in all_keys.items():
        jwks.append({
            **key.export(private_key=False, as_dict=True),
            "kid": kid,
            "use": "sig",
            "alg": settings.JWK_ALGORITHM,
        })
    return {"keys": jwks}