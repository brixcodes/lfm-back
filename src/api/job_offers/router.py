from datetime import date, datetime, timezone
import sys
from typing import Annotated
from fastapi import APIRouter, Depends, Form, File, HTTPException, Query, status
from fastapi import UploadFile

from src.api.auth.utils import check_permissions
from src.api.payments.schemas import PaymentInitInput
from src.api.payments.service import PaymentService
from src.api.user.models import PermissionEnum, User
from src.helper.schemas import BaseOutFail, ErrorMessage
from src.helper.utils import clean_payment_description

from src.api.job_offers.service import JobOfferService
from src.api.job_offers.schemas import (
    JobAttachmentInput,
    JobOfferCreateInput,
    JobOfferUpdateInput,
    JobOfferOutSuccess,
    JobOffersPageOutSuccess,
    JobOfferFilter,
    JobApplicationCreateInput,
    JobApplicationUpdateInput,
    JobApplicationUpdateByCandidateInput,
    JobApplicationOTPRequestInput,
    JobApplicationOutSuccess,
    JobApplicationsPageOutSuccess,
    JobApplicationFilter,
    JobAttachmentOutSuccess,
    JobAttachmentListOutSuccess,
    PaymentJobApplicationOutSuccess,
    UpdateJobOfferStatusInput,
)
from src.api.job_offers.dependencies import get_job_offer, get_job_application, get_job_attachment


router = APIRouter(tags=["Job Offers"])


# Job Offers
@router.get("/job-offers", response_model=JobOffersPageOutSuccess, tags=["Job Offer"])
async def list_job_offers(
    filters: Annotated[JobOfferFilter, Query(...)],
    job_offer_service: JobOfferService = Depends(),
):
    job_offers, total = await job_offer_service.list_job_offers(filters)
    return {"data": job_offers, "page": filters.page, "number": len(job_offers), "total_number": total}


@router.post("/job-offers", response_model=JobOfferOutSuccess, tags=["Job Offer"])
async def create_job_offer(
    input: JobOfferCreateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CREATE_JOB_OFFER]))],
    job_offer_service: JobOfferService = Depends(),
):
    existing = await job_offer_service.get_job_offer_by_reference(input.reference)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_OFFER_REFERENCE_TAKEN.description,
                error_code=ErrorMessage.JOB_OFFER_REFERENCE_TAKEN.value,
            ).model_dump(),
        )
    job_offer = await job_offer_service.create_job_offer(input)
    return {"message": "Job offer created successfully", "data": job_offer}


@router.get("/job-offers/{job_offer_id}", response_model=JobOfferOutSuccess, tags=["Job Offer"])
async def get_job_offer_route(
    job_offer_id: str,
    job_offer=Depends(get_job_offer),
):
    return {"message": "Job offer fetched successfully", "data": job_offer}


@router.put("/job-offers/{job_offer_id}", response_model=JobOfferOutSuccess, tags=["Job Offer"])
async def update_job_offer_route(
    job_offer_id: str,
    input: JobOfferUpdateInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_UPDATE_JOB_OFFER]))],
    job_offer=Depends(get_job_offer),
    job_offer_service: JobOfferService = Depends(),
):
    if input.reference:
        existing = await job_offer_service.get_job_offer_by_reference(input.reference)
        if existing is not None and existing.id != job_offer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.JOB_OFFER_REFERENCE_TAKEN.description,
                    error_code=ErrorMessage.JOB_OFFER_REFERENCE_TAKEN.value,
                ).model_dump(),
            )
    job_offer = await job_offer_service.update_job_offer(job_offer, input)
    return {"message": "Job offer updated successfully", "data": job_offer}


@router.delete("/job-offers/{job_offer_id}", response_model=JobOfferOutSuccess, tags=["Job Offer"])
async def delete_job_offer_route(
    job_offer_id: str,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_JOB_OFFER]))],
    job_offer=Depends(get_job_offer),
    job_offer_service: JobOfferService = Depends(),
):
    job_offer = await job_offer_service.delete_job_offer(job_offer)
    return {"message": "Job offer deleted successfully", "data": job_offer}


# Job Applications
@router.get("/job-applications", response_model=JobApplicationsPageOutSuccess, tags=["Job Application"])
async def list_job_applications(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    filters: Annotated[JobApplicationFilter, Query(...)],
    job_offer_service: JobOfferService = Depends(),
):
    """Get only 'paid' job applications by default (TRANSFER all + ONLINE paid)"""
    # Force is_paid to True by default for the main endpoint
    if filters.is_paid is None:
        filters.is_paid = True
    applications, total = await job_offer_service.list_job_applications(filters)
    return {"data": applications, "page": filters.page, "number": len(applications), "total_number": total}

@router.get("/job-applications/paid", response_model=JobApplicationsPageOutSuccess, tags=["Job Application"])
async def list_paid_job_applications(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    filters: Annotated[JobApplicationFilter, Query(...)],
    job_offer_service: JobOfferService = Depends(),
):
    """Get only paid job applications"""
    # Force is_paid to True
    filters.is_paid = True
    applications, total = await job_offer_service.list_job_applications(filters)
    return {"data": applications, "page": filters.page, "number": len(applications), "total_number": total}

@router.get("/job-applications/unpaid", response_model=JobApplicationsPageOutSuccess, tags=["Job Application"])
async def list_unpaid_job_applications(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    filters: Annotated[JobApplicationFilter, Query(...)],
    job_offer_service: JobOfferService = Depends(),
):
    """Get only unpaid job applications"""
    # Force is_paid to False
    filters.is_paid = False
    applications, total = await job_offer_service.list_job_applications(filters)
    return {"data": applications, "page": filters.page, "number": len(applications), "total_number": total}

@router.get("/job-applications/all", response_model=JobApplicationsPageOutSuccess, tags=["Job Application"])
async def list_all_job_applications(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    filters: Annotated[JobApplicationFilter, Query(...)],
    job_offer_service: JobOfferService = Depends(),
):
    """Get all job applications (both paid and unpaid)"""
    # Force is_paid to None to show all applications
    filters.is_paid = None
    applications, total = await job_offer_service.list_job_applications(filters)
    return {"data": applications, "page": filters.page, "number": len(applications), "total_number": total}

@router.get("/job-applications/payment-stats", tags=["Job Application"])
async def get_job_applications_payment_stats(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    job_offer_service: JobOfferService = Depends(),
):
    """Get statistics about job applications payment status"""
    stats = await job_offer_service.get_payment_statistics()
    return stats

@router.get("/job-applications/{application_id}/attachments", response_model=JobAttachmentListOutSuccess, tags=["Job Application"])
async def list_job_attachments(
    application_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    job_offer_service: JobOfferService = Depends(),
):
    """List attachments for a job application"""
    attachments = await job_offer_service.list_attachments_by_application(application_id)
    return {"message": "Attachments fetched successfully", "data": attachments}

@router.get("/job-attachments/{attachment_id}/download", tags=["Job Application"])
async def download_job_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    job_offer_service: JobOfferService = Depends(),
):
    """Download a job application attachment"""
    attachment = await job_offer_service.get_job_attachment_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Attachment not found",
                error_code="ATTACHMENT_NOT_FOUND"
            ).model_dump(),
        )
    
    # Return the file path for download
    return {"download_url": attachment.file_path}

@router.post("/job-applications/change-status", response_model=JobApplicationOutSuccess, tags=["Job Application"])
async def change_job_application_status(
    input: UpdateJobOfferStatusInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_CHANGE_JOB_APPLICATION_STATUS]))],
    job_offer_service: JobOfferService = Depends(),
):
    application = await job_offer_service.get_job_application_by_id(input.application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.JOB_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    
    if application.payment_id == None :
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.CANNOT_APPROVE_UNPAID_APPLICATION.description,
                error_code=ErrorMessage.CANNOT_APPROVE_UNPAID_APPLICATION.value,
            ).model_dump(),
        )
    
    application = await job_offer_service.change_job_application_status(application=application, input=input)
    return {"message": "Job application fetched successfully", "data": application}

@router.post("/job-applications", response_model=PaymentJobApplicationOutSuccess, tags=["Job Application"])
async def create_job_application(
    input: JobApplicationCreateInput,
    job_offer_service: JobOfferService = Depends(),
    payment_service: PaymentService = Depends()
):
    
    # Verify job offer exists
    job_offer = await job_offer_service.get_job_offer_by_id(input.job_offer_id)
    if job_offer is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_OFFER_NOT_FOUND.description,
                error_code=ErrorMessage.JOB_OFFER_NOT_FOUND.value,
            ).model_dump(),
        )
    
    
    if job_offer.submission_deadline < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_OFFER_CLOSED.description,
                error_code=ErrorMessage.JOB_OFFER_CLOSED.value,
            ).model_dump(),
        )
    # Vérifier que tous les attachments requis sont présents
    if job_offer.attachment:
        submitted_attachment_types = []
        if input.attachments:
            submitted_attachment_types = [val.type for val in input.attachments]
        
        required_attachments = job_offer.attachment
        print(f"DEBUG: Required attachments: {required_attachments}")
        print(f"DEBUG: Submitted attachments: {submitted_attachment_types}")
        
        for required_attachment in required_attachments:
            if required_attachment not in submitted_attachment_types:
                print(f"DEBUG: Missing required attachment: {required_attachment}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=BaseOutFail(
                        message=f"Job attachment '{required_attachment}' is required",
                        error_code=ErrorMessage.JOB_ATTACHMENT_REQUIRED.value,
                    ).model_dump(),
                )
    
    application = await job_offer_service.create_job_application(job_offer=job_offer, data=input)

    # If transfer, require receipt and skip payment initiation
    if input.payment_method == "TRANSFER":
        submitted_types = [att.type for att in (input.attachments or [])]
        if "BANK_TRANSFER_RECEIPT" not in submitted_types:
            await job_offer_service.delete_job_application(application)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message="Bank transfer receipt is required",
                    error_code=ErrorMessage.JOB_ATTACHMENT_REQUIRED.value,
                ).model_dump(),
            )
        await job_offer_service.send_application_confirmation_email(application)
        return {"message": "Job application created successfully", "data": {
            "job_application": application,
            "payment": None
        }}

    # Default ONLINE: initiate payment
    description = clean_payment_description(f"Frais de candidature au poste de {job_offer.title}")
    payment_input = PaymentInitInput(
        payable=application,
        amount=job_offer.submission_fee,
        product_currency=job_offer.currency,
        description=description,
        payment_provider="CINETPAY",
        customer_name=input.last_name,
        customer_surname=input.first_name,
        customer_email=input.email,
        customer_phone_number=input.phone_number,
        customer_address=input.address,
        customer_city=input.city,
        customer_country=input.country_code,
        customer_state=input.country_code,
        customer_zip_code="00000"
    )

    try:
        payment = await payment_service.initiate_payment(payment_input)
    except Exception as e:
        print(e.with_traceback(sys.exc_info()[2]))
        await job_offer_service.delete_job_application(application)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.PAYMENT_INITIATION_FAILED.description,
                error_code=ErrorMessage.PAYMENT_INITIATION_FAILED.value,
            ).model_dump(),
        )

    if payment.get("success") is False:
        await job_offer_service.delete_job_application(application)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.PAYMENT_INITIATION_FAILED.description + " (" + payment.get("message", "") + ")",
                error_code=ErrorMessage.PAYMENT_INITIATION_FAILED.value,
            ).model_dump(),
        )

    await job_offer_service.send_application_confirmation_email(application)
    return {"message": "Job application created successfully", "data": {
        "job_application": application,
        "payment": payment
    }}

@router.get("/job-applications/{application_id}", response_model=JobApplicationOutSuccess, tags=["Job Application"])
async def get_job_application_route(
    application_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    job_offer_service: JobOfferService = Depends(),
):
    full_application = await job_offer_service.get_full_job_application_by_id(application_id)
    if full_application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.JOB_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    return {"message": "Job application fetched successfully", "data": full_application}

@router.post("/job-attachments", response_model=JobAttachmentListOutSuccess, tags=["Job Attachment"])
async def create_attachment(
    name: str = Form(...),
    file: UploadFile = File(...),
    job_offer_service: JobOfferService = Depends(),
):
    # Créer l'objet JobAttachmentInput manuellement
    input_data = JobAttachmentInput(name=name, file=file)
    attachment = await job_offer_service.create_job_attachment(input_data)
    return {"message": "Attachment created successfully", "data": [attachment]}

# Job Attachments
@router.get("/job-applications/{application_id}/attachments", response_model=JobAttachmentListOutSuccess, tags=["Job Attachment"])
async def list_attachments(
    application_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_JOB_APPLICATION]))],
    application=Depends(get_job_application),
    job_offer_service: JobOfferService = Depends(),
):
    attachments = await job_offer_service.list_attachments_by_application(application_id)
    return {"message": "Attachments fetched successfully", "data": attachments}


@router.delete("/job-attachments/{attachment_id}", response_model=JobAttachmentOutSuccess, tags=["Job Attachment"])
async def delete_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_DELETE_JOB_ATTACHMENT]))],
    attachment=Depends(get_job_attachment),
    job_offer_service: JobOfferService = Depends(),
):
    attachment = await job_offer_service.delete_job_attachment(attachment)
    return {"message": "Attachment deleted successfully", "data": attachment}



# OTP Endpoints for Job Applications
@router.post("/job-applications/request-otp", tags=["Job Application OTP"])
async def request_application_otp(
    input: JobApplicationOTPRequestInput,
    job_offer_service: JobOfferService = Depends(),
):
    """Request OTP code to update job application"""
    code = await job_offer_service.generate_application_otp(input.application_number, input.email)
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.JOB_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.JOB_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    
    # OTP code has been sent via email
    return {"message": "OTP code sent to your email address", "data": {}}


@router.put("/job-applications/update-by-candidate", response_model=JobApplicationOutSuccess, tags=["Job Application OTP"])
async def update_application_by_candidate(
    input: JobApplicationUpdateByCandidateInput,
    job_offer_service: JobOfferService = Depends(),
):
    """Update job application by candidate using OTP verification"""
    # Verify OTP and get application
    # We need to get application_number from somewhere - let's add it to the input schema
    # For now, let's assume it's passed in the input
    application = await job_offer_service.verify_application_otp(
        input.application_number, input.email, input.otp_code
    )
    
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.INVALID_OTP_OR_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.INVALID_OTP_OR_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    
    
    # Update application
    updated_application = await job_offer_service.update_application_by_candidate(application, input)
    return {"message": "Application updated successfully", "data": updated_application}
