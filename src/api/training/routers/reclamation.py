from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query ,status
from src.api.auth.utils import check_permissions, get_current_active_user
from src.api.training.services.student_application import StudentApplicationService
from src.api.user.models import PermissionEnum, User
from src.api.training.services import ReclamationService
from src.api.training.schemas import (
    ReclamationCreateInput,
    ReclamationAdminUpdateInput,
    ReclamationOutSuccess,
    ReclamationTypeUpdateInput,
    ReclamationsPageOutSuccess,
    ReclamationFilter,
    ReclamationTypeCreateInput,
    ReclamationTypeOutSuccess,
    ReclamationTypeListOutSuccess,
)
from src.api.training.dependencies import (
    get_reclamation,
    get_user_reclamation,
)
from src.helper.schemas import BaseOutFail, ErrorMessage

router = APIRouter()

# User Reclamation Endpoints
@router.post("/my-reclamations", response_model=ReclamationOutSuccess, tags=["My Reclamations"])
async def create_my_reclamation(
    input: ReclamationCreateInput,
    current_user: Annotated[User, Depends(get_current_active_user)],
    reclamation_service: ReclamationService = Depends(),
    student_app_service: StudentApplicationService = Depends(),
):
    """Create a new reclamation by user"""
    # TODO: Validate that application_number belongs to current user
    application = await student_app_service.get_student_application_by_application_number(input.application_number,current_user.id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
        
    reclamation = await reclamation_service.create_reclamation(input, user_id=current_user.id)
    return {"message": "Reclamation created successfully", "data": reclamation}


@router.get("/my-reclamations", response_model=ReclamationsPageOutSuccess, tags=["My Reclamations"])
async def list_my_reclamations(
    filters: Annotated[ReclamationFilter, Query(...)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    reclamation_service: ReclamationService = Depends(),
):
    """Get paginated list of user's own reclamations"""
    reclamations, total = await reclamation_service.list_user_reclamations(current_user.id, filters)
    return {
        "data": reclamations,
        "page": filters.page,
        "number": len(reclamations),
        "total_number": total,
        "message": "User reclamations fetched successfully"
    }


@router.get("/my-reclamations/{reclamation_id}", response_model=ReclamationOutSuccess, tags=["My Reclamations"])
async def get_my_reclamation(
    reclamation_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    reclamation_service: ReclamationService = Depends(),
):
    reclamation = await reclamation_service.get_reclamation_by_id(reclamation_id, user_id=current_user.id)
    if reclamation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Reclamation not found",
                error_code="RECLAMATION_NOT_FOUND",
            ).model_dump(),
        )
    
    return {"message": "Reclamation fetched successfully", "data": reclamation}


@router.put("/my-reclamations/{reclamation_id}", response_model=ReclamationOutSuccess, tags=["My Reclamations"])
async def update_my_reclamation(
    reclamation_id: int,
    input: ReclamationCreateInput,
    current_user: Annotated[User, Depends(get_current_active_user)],
    reclamation_service: ReclamationService = Depends(),
    student_app_service: StudentApplicationService = Depends(),
):
    """Update a reclamation by user"""
    # Vérifier que la réclamation appartient à l'utilisateur
    existing_reclamation = await reclamation_service.get_reclamation_by_id(reclamation_id, user_id=current_user.id)
    if existing_reclamation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Reclamation not found",
                error_code="RECLAMATION_NOT_FOUND",
            ).model_dump(),
        )
    
    # Vérifier que la candidature appartient à l'utilisateur
    application = await student_app_service.get_student_application_by_application_number(input.application_number, current_user.id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    
    # Mettre à jour la réclamation
    updated_reclamation = await reclamation_service.update_reclamation(reclamation_id, input, user_id=current_user.id)
    return {"message": "Reclamation updated successfully", "data": updated_reclamation}


@router.delete("/my-reclamations/{reclamation_id}", response_model=ReclamationOutSuccess, tags=["My Reclamations"])
async def delete_my_reclamation(
    reclamation_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    reclamation_service: ReclamationService = Depends(),
):
    """Delete a reclamation by user"""
    # Vérifier que la réclamation appartient à l'utilisateur
    existing_reclamation = await reclamation_service.get_reclamation_by_id(reclamation_id, user_id=current_user.id)
    if existing_reclamation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Reclamation not found",
                error_code="RECLAMATION_NOT_FOUND",
            ).model_dump(),
        )
    
    # Supprimer la réclamation (soft delete)
    deleted_reclamation = await reclamation_service.delete_reclamation(existing_reclamation)
    return {"message": "Reclamation deleted successfully", "data": deleted_reclamation}


# Admin Reclamation Endpoints
@router.get("/reclamations", response_model=ReclamationsPageOutSuccess, tags=["Admin Reclamations"])
async def list_all_reclamations_admin(
    filters: Annotated[ReclamationFilter, Query(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_RECLAMATION]))],
    reclamation_service: ReclamationService = Depends(),
):
    """Get paginated list of all reclamations (admin)"""
    reclamations, total = await reclamation_service.list_all_reclamations(filters)
    return {
        "data": reclamations,
        "page": filters.page,
        "number": len(reclamations),
        "total_number": total,
        "message": "All reclamations fetched successfully"
    }


@router.get("/reclamations/{reclamation_id}", response_model=ReclamationOutSuccess, tags=["Admin Reclamations"])
async def get_reclamation_admin(
    reclamation_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_RECLAMATION]))],
    reclamation=Depends(get_reclamation),
):
    """Get reclamation by ID (admin)"""
    return {"message": "Reclamation fetched successfully", "data": reclamation}


@router.put("/reclamations/{reclamation_id}/status", response_model=ReclamationOutSuccess, tags=["Admin Reclamations"])
async def update_reclamation_status(
    reclamation_id: int,
    input: ReclamationAdminUpdateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CHANGE_RECLAMATION_STATUS]))],
    reclamation=Depends(get_reclamation),
    reclamation_service: ReclamationService = Depends(),
):
    """Update reclamation status and assign admin (admin)"""
    reclamation = await reclamation_service.update_reclamation_status(reclamation, input)
    return {"message": "Reclamation status updated successfully", "data": reclamation}




# Reclamation Types Endpoints
@router.get("/reclamation-types/active/all", response_model=ReclamationTypeListOutSuccess, tags=["Reclamation Types"])
async def get_active_reclamation_types(
    reclamation_service: ReclamationService = Depends(),
):
    """Get all active reclamation types for dropdown lists"""
    types = await reclamation_service.get_all_reclamation_types()
    return {"data": types, "message": "Active reclamation types fetched successfully"}


@router.post("/reclamation-types", response_model=ReclamationTypeOutSuccess, tags=["Reclamation Types"])
async def create_reclamation_type(
    input: ReclamationTypeCreateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_RECLAMATION_TYPE]))],
    reclamation_service: ReclamationService = Depends(),
):
    """Create a new reclamation type (admin)"""
    reclamation_type = await reclamation_service.create_reclamation_type(input)
    return {"message": "Reclamation type created successfully", "data": reclamation_type}

@router.get("/reclamation-types/{type_id}", response_model=ReclamationTypeOutSuccess, tags=["Reclamation Types"])
async def get_reclamation_type(
    type_id: int,
    reclamation_service: ReclamationService = Depends(),
):
    """Get reclamation type by ID"""
    reclamation_type = await reclamation_service.get_reclamation_type_by_id(type_id)
    if reclamation_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Reclamation type not found",
                error_code="RECLAMATION_TYPE_NOT_FOUND",
            ).model_dump(),
        )
    return {"message": "Reclamation type fetched successfully", "data": reclamation_type}


@router.put("/reclamation-types/{type_id}", response_model=ReclamationTypeOutSuccess, tags=["Reclamation Types"])
async def update_reclamation_type(
    type_id: int,
    input: ReclamationTypeUpdateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_RECLAMATION_TYPE]))],
    reclamation_service: ReclamationService = Depends(),
):
    """Update reclamation type (admin)"""
    reclamation_type = await reclamation_service.get_reclamation_type_by_id(type_id)
    if reclamation_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Reclamation type not found",
                error_code="RECLAMATION_TYPE_NOT_FOUND",
            ).model_dump(),
        )
    
    reclamation_type = await reclamation_service.update_reclamation_type(reclamation_type, input)
    return {"message": "Reclamation type updated successfully", "data": reclamation_type}


@router.delete("/reclamation-types/{type_id}", response_model=ReclamationTypeOutSuccess, tags=["Reclamation Types"])
async def delete_reclamation_type(
    type_id: int,
current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_RECLAMATION_TYPE]))],
    reclamation_service: ReclamationService = Depends(),
):
    """Delete reclamation type (admin)"""
    reclamation_type = await reclamation_service.delete_reclamation_type(type_id)
    return {"message": "Reclamation type deleted successfully", "data": reclamation_type}