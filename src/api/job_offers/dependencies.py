from fastapi import HTTPException, Depends, status

from src.helper.schemas import BaseOutFail, ErrorMessage
from src.api.job_offers.service import JobOfferService


async def get_job_offer(job_offer_id: str, job_offer_service: JobOfferService = Depends()):
    job_offer = await job_offer_service.get_job_offer_by_id(job_offer_id)
    if job_offer is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_OFFER_NOT_FOUND.description,
                error_code=ErrorMessage.JOB_OFFER_NOT_FOUND.value,
            ).model_dump(),
        )
    return job_offer


async def get_job_application(application_id: int, job_offer_service: JobOfferService = Depends()):
    job_application = await job_offer_service.get_job_application_by_id(application_id)
    if job_application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.JOB_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    return job_application


async def get_job_attachment(attachment_id: int, job_offer_service: JobOfferService = Depends()):
    attachment = await job_offer_service.get_job_attachment_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_ATTACHMENT_NOT_FOUND.description,
                error_code=ErrorMessage.JOB_ATTACHMENT_NOT_FOUND.value,
            ).model_dump(),
        )
    return attachment
