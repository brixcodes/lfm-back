from fastapi import HTTPException, Depends,status

from src.helper.schemas import BaseOutFail, ErrorMessage

from src.api.user.service import UserService


async def get_user(user_id: str, user_service: UserService = Depends()):
    
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.USER_NOT_FOUND.description,
                    error_code= ErrorMessage.USER_NOT_FOUND.value
                ).model_dump()
        )
    return user
