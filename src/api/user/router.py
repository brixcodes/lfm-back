from fastapi import APIRouter, Depends, HTTPException, Query,status
from typing import Annotated

from src.helper.utils import NotificationHelper
from src.redis_client import get_from_redis, set_to_redis

from src.api.auth.utils import  check_permissions, get_current_active_user, require_oauth_client
from src.api.user.dependencies import get_user
from src.api.user.models import PermissionEnum, RoleEnum, User
from src.helper.schemas import BaseOutFail, ErrorMessage
from src.api.user.service import UserService
from src.api.user.schemas import ( AssignPermissionsInput, AssignRoleInput, CreateUserInput, PermissionListOutSuccess, PermissionSmallListOutSuccess, RoleListOutSuccess, RoleOutSuccess, UpdateStatusInput, UpdateUserInput, UserFilter, UserListInput, UserListOutSuccess, UserOutSuccess, UsersPageOutSuccess)

router = APIRouter()


@router.post('/users/assign-permissions',response_model=PermissionListOutSuccess,tags=["Role And Permission"])
async def assign_permissions(
    input : AssignPermissionsInput,
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_GIVE_PERMISSION]))],
    user_service: UserService = Depends()
):
    
    await user_service.assign_permissions(user_id=input.user_id, permissions=input.permissions)
    
    user_permissions = await user_service.get_all_user_permissions(user_id=input.user_id)
    
    return  { "message" : "Permissions assigned successfully", "data" : user_permissions }
    

@router.post('/users/revoke-permissions',response_model=PermissionListOutSuccess,tags=["Role And Permission"])
async def revoke_permissions(
    input : AssignPermissionsInput,
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_GIVE_PERMISSION]))],
    user_service: UserService = Depends()
):
    
    await user_service.revoke_permissions(user_id=input.user_id, permissions=input.permissions)
    
    user_permissions = await user_service.get_all_user_permissions(user_id=input.user_id)
    
    return  { "message" : "Permissions revoked successfully", "data" : user_permissions }

@router.post('/users/assign-roles',response_model=PermissionListOutSuccess,tags=["Role And Permission"])
async def assign_roles(
    input : AssignRoleInput,
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_GIVE_PERMISSION]))],
    user_service: UserService = Depends()
):
    
    await user_service.assign_role(user_id=input.user_id, role_id=input.role_id)
    
    user_permissions = await user_service.get_all_user_permissions(user_id=input.user_id)
    
    return  { "message" : "Roles assigned successfully", "data" : user_permissions }

@router.post('/users/revoke-role',response_model=PermissionListOutSuccess,tags=["Role And Permission"])
async def revoke_roles(
    input : AssignRoleInput,
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_GIVE_PERMISSION]))],
    user_service: UserService = Depends()
):
    
    await user_service.revoke_role(user_id=input.user_id, role_id=input.role_id)
    
    user_permissions = await user_service.get_all_user_permissions(user_id=input.user_id)
    
    return  { "message" : "Roles revoked successfully", "data" : user_permissions }

@router.get('/users/permissions/{user_id}',response_model=PermissionListOutSuccess,tags=["Role And Permission"])
async def get_user_permissions(
    user_id : str,
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_GIVE_PERMISSION]))],
    user_service: UserService = Depends()
):
    
    user_permissions = await user_service.get_all_user_permissions(user_id=user_id)
    
    return  { "message" : "User Permissions", "data" : user_permissions }


@router.get('/users/role/{user_id}',response_model=RoleOutSuccess,tags=["Role And Permission"])
async def get_user_role(
    user_id : str,
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_GIVE_PERMISSION]))],
    user_service: UserService = Depends()
):
    
    user_role = await user_service.get_user_role(user_id=user_id)
    
    if len(user_role) == 0  :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.ROLE_NOT_FOUND.description,
                    error_code= ErrorMessage.ROLE_NOT_FOUND.value
                ).model_dump()
        )
    
    return  { "message" : "User Permissions", "data" : user_role[0] }

@router.get("/users", response_model=UsersPageOutSuccess,tags=["Users"])
async def read_user_list( 
        current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_USER]))],
        filter_query: Annotated[UserFilter, Query(...)],
        user_service: UserService = Depends()
    ):

    users , counted  = await user_service.get(user_filter=filter_query)
    
    return {
        "data": users,
        "page": filter_query.page,
        "number": len(users),
        "total_number": counted,
    }

@router.post("/users", response_model=UserOutSuccess,tags=["Users"])
async def create_user( 
        user_create_input: CreateUserInput,
        current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_USER]))],
        user_service: UserService = Depends()
    ):
    
    email_user = await user_service.get_by_email(user_create_input.email)
    if email_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,            
            detail=BaseOutFail(
                message=ErrorMessage.EMAIL_ALREADY_TAKEN.description,
                error_code= ErrorMessage.EMAIL_ALREADY_TAKEN.value
            ).model_dump()
        )

    users = await user_service.create(user_create_input)
    return  {"data" : users, "message":"Users created successfully" }

@router.post("/users/internal", response_model=UserListOutSuccess,tags=["Users"])
async def read_user_list( input: UserListInput , user_service: UserService = Depends(),claims = Depends(require_oauth_client({"user:read"}))):

    users = await user_service.get_users_by_id_lists(user_ids=input.user_ids)
    return  {"data" : users, "message":"Users list fetch successfully" }


@router.get("/users/{user_id}", response_model=UserOutSuccess,tags=["Users"])
async def read_user_by_id(current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_USER]))],user : Annotated[User, Depends(get_user)]):
    
    return  {"data" : user, "message":"Users fetch successfully" }



@router.post("/users/change-status/{user_id}", response_model=UserOutSuccess,tags=["Users"])
async def update_user_status(
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_USER]))],
    user_id: str,
    user_update_input: UpdateStatusInput,
    user : Annotated[User, Depends(get_user)],
    user_service: UserService = Depends(),
):
    
    user = await user_service.update_user_status(user_id, user_update_input.status)
    
    return  {"data" : user, "message":"Users updated status successfully" }


@router.put("/users/{user_id}", response_model=UserOutSuccess,tags=["Users"])
async def update_user(
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_USER]))],
    user_id: str,
    user_update_input: UpdateUserInput,
    user : Annotated[User, Depends(get_user)],
    user_service: UserService = Depends(),
):
    user_email = await user_service.get_by_email(user_email=user_update_input.email)
    if user_email is not None and user_email.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,            
            detail=BaseOutFail(
                message=ErrorMessage.EMAIL_ALREADY_TAKEN.description,
                error_code= ErrorMessage.EMAIL_ALREADY_TAKEN.value
            ).model_dump()
        )
        
    
    user = await user_service.update(user_id, user_update_input)
    
    return  {"data" : user, "message":"Users updated successfully" }


@router.delete("/users/{user_id}",response_model=UserOutSuccess,tags=["Users"])
async def delete_user(
    user_id: str,
    user : Annotated[User, Depends(get_user)],
    user_service: UserService = Depends(),
):
    val = await user_service.has_any_role(user_id, [RoleEnum.SUPER_ADMIN])
    
    if val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,            
            detail=BaseOutFail(
                message=ErrorMessage.CAN_NOT_DELETE_SUPER_ADMIN.description,
                error_code= ErrorMessage.CAN_NOT_DELETE_SUPER_ADMIN.value
            ).model_dump()
        )
    user = await user_service.delete_user(user_id)
    return {"data" : user, "message":"Users updated successfully" }   


@router.get('/roles',response_model=RoleListOutSuccess,tags=["Role And Permission"])
async def get_roles(
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_ROLE]))],
    user_service: UserService = Depends()):
    roles = await user_service.get_all_roles()
    return  {"data" : roles, "message":"Roles fetch successfully" }

@router.get('/permissions',response_model=PermissionSmallListOutSuccess ,tags=["Role And Permission"])
async def get_permissions(
    current_user : Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_ROLE]))],
    user_service: UserService = Depends()):
    permissions = await user_service.get_all_permissions()
    return  {"data" : permissions, "message":"Permissions fetch successfully" }



@router.get('/setup-users',tags=["Users"])
async def setup_users(user_service: UserService = Depends()):
    await user_service.permission_set_up()
    
    return  {"data" : "Users setup successfully" }




@router.get('/test-get-data-to-redis',tags=["Test"])
async def get_data_redis(test_number : int):
    cached = await get_from_redis(f"test:{test_number}")
    if cached:
        return  {"data" : cached }

    return  {"message" : "no data" }
    
@router.get('/test-add-data-to-redis',tags=["Test"])
async def add_data_redis(test_number : int):
    await set_to_redis(
                        f"test:{test_number}", f"test:{test_number}", ex=60
                    ) 
    cached = await get_from_redis(f"test:{test_number}")
    if cached:
        return  {"data" : cached }

    return  {"message" : "npo data found after add" }

@router.get('/test-send-email',tags=["Test"])
async def test_email(email : str):
    
    data = {
            "to_email" : email,
            "subject":"Email Validation",
            "template_name":"verify_email.html" ,
            "lang":"en",
            "context":{
                    "code":"AZERTY",
                    "time": 30
                } 
        } 
    NotificationHelper.send_smtp_email(data=data)

    return  {"message" : "email send" }
