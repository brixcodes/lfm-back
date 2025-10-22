from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query ,status
from src.api.auth.utils import check_permissions
from src.api.system.service import OrganizationCenterService
from src.api.training.services.specialty import SpecialtyService
from src.api.user.models import PermissionEnum, User
from src.api.training.services import TrainingService
from src.api.training.schemas import (
    TrainingCreateInput,
    TrainingUpdateInput,
    TrainingOutSuccess,
    TrainingsPageOutSuccess,
    TrainingFilter,
    TrainingSessionCreateInput,
    TrainingSessionUpdateInput,
    TrainingSessionFilter,
    TrainingSessionOutSuccess,
    TrainingSessionsPageOutSuccess,
)
from src.api.training.dependencies import (
    get_training,
    get_training_session,
)
from src.api.user.schemas import UserListOutSuccess
from src.helper.schemas import BaseOutFail, ErrorMessage

router = APIRouter()


# Trainings
@router.get("/trainings", response_model=TrainingsPageOutSuccess, tags=["Training"])
async def list_trainings(
    filters: Annotated[TrainingFilter, Query(...)],
    training_service: TrainingService = Depends(),
):
    trainings, total = await training_service.list_trainings(filters)
    return {"data": trainings, "page": filters.page, "number": len(trainings), "total_number": total}


@router.post("/trainings", response_model=TrainingOutSuccess, tags=["Training"])
async def create_training(
    input: TrainingCreateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CREATE_TRAINING]))],
    training_service: TrainingService = Depends(),specialty_service: SpecialtyService = Depends(),
):
    specialty = await specialty_service.get_specialty_by_id(input.specialty_id)
    if specialty is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.SPECIALTY_NOT_FOUND.description,
                error_code=ErrorMessage.SPECIALTY_NOT_FOUND.value
            ).model_dump()
        )
    training = await training_service.create_training(input)
    return {"message": "Training created successfully", "data": training}


@router.get("/trainings/{training_id}", response_model=TrainingOutSuccess, tags=["Training"])
async def get_training_route(
    training_id: str,
    training=Depends(get_training),
):
    return {"message": "Training fetched successfully", "data": training}


@router.put("/trainings/{training_id}", response_model=TrainingOutSuccess, tags=["Training"])
async def update_training_route(
    training_id: str,
    input: TrainingUpdateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_TRAINING]))],
    training=Depends(get_training),
    training_service: TrainingService = Depends(),specialty_service: SpecialtyService = Depends(),
):
    if input.specialty_id is not None:
        
        specialty = await specialty_service.get_specialty_by_id(input.specialty_id)
        if specialty is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.SPECIALTY_NOT_FOUND.description,
                    error_code=ErrorMessage.SPECIALTY_NOT_FOUND.value
                ).model_dump()
        )
    training = await training_service.update_training(training, input)
    return {"message": "Training updated successfully", "data": training}


@router.delete("/trainings/{training_id}", response_model=TrainingOutSuccess, tags=["Training"])
async def delete_training_route(
    training_id: str,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_TRAINING]))],
    training=Depends(get_training),
    training_service: TrainingService = Depends(),
):
    training = await training_service.delete_training(training)
    return {"message": "Training deleted successfully", "data": training}


# Training Sessions
@router.get("/training-sessions", response_model=TrainingSessionsPageOutSuccess, tags=["Training Session"])
async def list_training_sessions(
    filters: Annotated[TrainingSessionFilter, Query(...)],
    training_service: TrainingService = Depends(),
):
    sessions, total = await training_service.list_training_sessions(filters)
    return {"data": sessions, "page": filters.page, "number": len(sessions), "total_number": total}


@router.get("/trainings/{training_id}/sessions", response_model=TrainingSessionsPageOutSuccess, tags=["Training Session"])
async def get_training_sessions_by_training_id(
    training_id: str,
    filters: Annotated[TrainingSessionFilter, Query(...)],
    training_service: TrainingService = Depends(),
):
    """Récupérer les sessions d'une formation par son ID"""
    # Vérifier que la formation existe
    training = await training_service.get_training_by_id(training_id)
    if training is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message=ErrorMessage.TRAINING_NOT_FOUND.description,
                error_code=ErrorMessage.TRAINING_NOT_FOUND.value,
            ).model_dump(),
        )
    
    # Ajouter le training_id aux filtres
    filters.training_id = training_id
    sessions, total = await training_service.list_training_sessions(filters)
    return {"data": sessions, "page": filters.page, "number": len(sessions), "total_number": total}


@router.post("/training-sessions", response_model=TrainingSessionOutSuccess, tags=["Training Session"])
async def create_training_session(
    input: TrainingSessionCreateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CREATE_TRAINING_SESSION]))],
    training_service: TrainingService = Depends(),
    org_service: OrganizationCenterService = Depends(),
):
    if input.center_id is not None:
        org = await org_service.get_by_id(input.center_id)
        if org is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.ORGANIZATION_CENTER_NOT_FOUND.description,
                    error_code=ErrorMessage.ORGANIZATION_CENTER_NOT_FOUND.value
                ).model_dump()
            )
            
    training = await training_service.get_training_by_id(input.training_id)
    if training is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.TRAINING_NOT_FOUND.description,
                error_code=ErrorMessage.TRAINING_NOT_FOUND.value,
            ).model_dump(),
        )
    session = await training_service.create_training_session(input)
    return {"message": "Training session created successfully", "data": session}


@router.get("/training-sessions/{session_id}/members", response_model=UserListOutSuccess, tags=["Training Session"])
async def get_training_session_members(
    session_id: str,
    training_session=Depends(get_training_session),
    training_service: TrainingService = Depends(),
):
    
    members = await training_service.get_training_session_members(session_id)
    return {"message": "Training session members fetched successfully", "data": members}

@router.get("/training-sessions/{session_id}", response_model=TrainingSessionOutSuccess, tags=["Training Session"])
async def get_training_session_route(
    session_id: str,
    training_session=Depends(get_training_session),
):
    return {"message": "Training session fetched successfully", "data": training_session}


@router.put("/training-sessions/{session_id}", response_model=TrainingSessionOutSuccess, tags=["Training Session"])
async def update_training_session_route(
    session_id: str,
    input: TrainingSessionUpdateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_TRAINING_SESSION]))],
    training_session=Depends(get_training_session),
    training_service: TrainingService = Depends(),
):
    training_session = await training_service.update_training_session(training_session, input)
    return {"message": "Training session updated successfully", "data": training_session}


@router.delete("/training-sessions/{session_id}", response_model=TrainingSessionOutSuccess, tags=["Training Session"])
async def delete_training_session_route(
    session_id: str,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_TRAINING_SESSION]))],
    training_session=Depends(get_training_session),
    training_service: TrainingService = Depends(),
):
    training_session = await training_service.delete_training_session(training_session)
    return {"message": "Training session deleted successfully", "data": training_session}