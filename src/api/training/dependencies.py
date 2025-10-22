from fastapi import HTTPException, Depends, status

from src.helper.schemas import BaseOutFail, ErrorMessage
from src.api.training.services import TrainingService , StudentApplicationService ,ReclamationService ,SpecialtyService



async def get_training(training_id: str, training_service: TrainingService = Depends()):
    training = await training_service.get_training_by_id(training_id)
    if training is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.TRAINING_NOT_FOUND.description,
                error_code=ErrorMessage.TRAINING_NOT_FOUND.value,
            ).model_dump(),
        )
    return training


async def get_training_session(session_id: str, training_service: TrainingService = Depends()):
    session = await training_service.get_training_session_by_id(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.TRAINING_SESSION_NOT_FOUND.description,
                error_code=ErrorMessage.TRAINING_SESSION_NOT_FOUND.value,
            ).model_dump(),
        )
    return session


async def get_student_application(application_id: int, service: StudentApplicationService = Depends()):
    application = await service.get_student_application_by_id(application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    return application


async def get_student_attachment(attachment_id: int, service: StudentApplicationService = Depends()):
    attachment = await service.get_student_attachment_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_ATTACHMENT_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_ATTACHMENT_NOT_FOUND.value,
            ).model_dump(),
        )
    return attachment


async def get_specialty(specialty_id: int, service: SpecialtyService = Depends()):
    specialty = await service.get_specialty_by_id(specialty_id)
    if specialty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Specialty not found",
                error_code="SPECIALTY_NOT_FOUND",
            ).model_dump(),
        )
    return specialty


async def get_reclamation(reclamation_id: int, service: ReclamationService = Depends()):
    reclamation = await service.get_reclamation_by_id(reclamation_id)
    if reclamation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Reclamation not found",
                error_code="RECLAMATION_NOT_FOUND",
            ).model_dump(),
        )
    return reclamation


async def get_user_reclamation(reclamation_id: int, service: ReclamationService = Depends()):
    """Get reclamation that belongs to current user"""
    reclamation = await service.get_reclamation_by_id(reclamation_id, user_id=None)
    if reclamation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Reclamation not found",
                error_code="RECLAMATION_NOT_FOUND",
            ).model_dump(),
        )
    return reclamation


