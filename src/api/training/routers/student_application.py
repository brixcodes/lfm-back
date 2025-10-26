from typing import Annotated
from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from src.api.auth.utils import check_permissions, get_current_active_user
from src.api.job_offers.models import ApplicationStatusEnum
from src.api.payments.schemas import InitPaymentOutSuccess
from src.api.user.models import PermissionEnum, User
from src.helper.schemas import BaseOutFail, ErrorMessage
from src.api.training.services import StudentApplicationService
from src.api.training.schemas import (
    ChangeStudentApplicationStatusInput,
    PayTrainingFeeInstallmentInput,
    StudentApplicationFilter,
    StudentApplicationsPageOutSuccess,
    StudentAttachmentInput,
    StudentApplicationCreateInput,
    StudentApplicationOutSuccess,
    StudentApplicationWithPaymentOutSuccess,
    StudentAttachmentOutSuccess,
    StudentAttachmentListOutSuccess,
    PaymentParametersInput,
    PaymentInfoOut,
)

router = APIRouter()

@router.get("/student-applications", response_model=StudentApplicationsPageOutSuccess, tags=["Student Application"])
async def list_student_applications_admin(
    input: Annotated[StudentApplicationFilter, Query(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    applications, total = await student_app_service.get_student_application(filters=input, user_id=None)
    
    return {"data": applications, "page": input.page, "number": len(applications), "total_number": total}

@router.get("/student-applications/payment-stats", tags=["Student Application"])
async def get_student_applications_payment_stats(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    """Get statistics about student applications payment status"""
    stats = await student_app_service.get_payment_statistics()
    return stats

@router.get("/student-applications/paid", response_model=StudentApplicationsPageOutSuccess, tags=["Student Application"])
async def list_paid_student_applications(
    input: Annotated[StudentApplicationFilter, Query(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    """Get only paid student applications"""
    # Force is_paid to True
    input.is_paid = True
    applications, total = await student_app_service.get_student_application(filters=input, user_id=None)
    
    return {"data": applications, "page": input.page, "number": len(applications), "total_number": total}

@router.get("/student-applications/unpaid", response_model=StudentApplicationsPageOutSuccess, tags=["Student Application"])
async def list_unpaid_student_applications(
    input: Annotated[StudentApplicationFilter, Query(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    """Get only unpaid student applications"""
    # Force is_paid to False
    input.is_paid = False
    applications, total = await student_app_service.get_student_application(filters=input, user_id=None)
    
    return {"data": applications, "page": input.page, "number": len(applications), "total_number": total}

@router.get("/student-applications/summary", tags=["Student Application"])
async def get_student_applications_summary(
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    """Get a summary of student applications with payment status"""
    # Get all applications
    all_applications, total = await student_app_service.get_student_application(
        filters=StudentApplicationFilter(page=1, page_size=1000), 
        user_id=None
    )
    
    # Get paid applications
    paid_applications, paid_total = await student_app_service.get_student_application(
        filters=StudentApplicationFilter(page=1, page_size=1000, is_paid=True), 
        user_id=None
    )
    
    # Get unpaid applications
    unpaid_applications, unpaid_total = await student_app_service.get_student_application(
        filters=StudentApplicationFilter(page=1, page_size=1000, is_paid=False), 
        user_id=None
    )
    
    # Calculate total revenue
    total_revenue = sum(
        (app.get('registration_fee', 0) or 0) + (app.get('training_fee', 0) or 0) 
        for app in paid_applications
    )
    
    return {
        "summary": {
            "total_applications": total,
            "paid_applications": paid_total,
            "unpaid_applications": unpaid_total,
            "payment_rate": round((paid_total / total * 100) if total > 0 else 0, 2),
            "total_revenue": total_revenue,
            "currency": "EUR"
        },
        "recent_paid": paid_applications[:5],  # Last 5 paid applications
        "recent_unpaid": unpaid_applications[:5]  # Last 5 unpaid applications
    }


@router.get("/student-applications/{application_id}", response_model=StudentApplicationOutSuccess, tags=["Student Application"])
async def get_student_application_admin(
    application_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    full_application = await student_app_service.get_full_student_application_by_id(application_id, user_id=None)
    if full_application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    return {"message": "Student application fetched successfully", "data": full_application}

@router.post("/student-applications/{application_id}/status", response_model=StudentApplicationOutSuccess, tags=["Student Application"])
async def change_student_application_status_admin(
    application_id: int,
    input : ChangeStudentApplicationStatusInput,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    application = await student_app_service.get_student_application_by_id(application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
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
        
    await student_app_service.change_student_application_status(application,input)
    full_application = await student_app_service.get_full_student_application_by_id(application_id, user_id=None)
    
    return {"message": "Student application fetched successfully", "data": full_application}

@router.get("/student-applications/{application_id}/attachments", response_model=StudentAttachmentListOutSuccess, tags=["Student Application"])
async def list_student_attachments(
    application_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    attachments = await student_app_service.list_attachments_by_application(application_id, user_id=None)
    return {"message": "Attachments fetched successfully", "data": attachments}

@router.get("/student-attachments/{attachment_id}/download", tags=["Student Application"])
async def download_student_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    """Download a student application attachment"""
    attachment = await student_app_service.get_student_attachment_by_id(attachment_id, user_id=None)
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


#eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YjczZjQ0Mi01NzVhLTQzNzgtODQ3Ny00MTUxMmU1ZjI5Y2MiLCJleHAiOjE3NTg1MTgzMjB9.S99P8yGi6fmN9LTONAm266a2GKW3uvEh54FVitbY6-k

#My  Student Applications
@router.post("/student-applications", response_model=StudentApplicationWithPaymentOutSuccess, tags=["My Student Application"])
async def create_student_application(
    input: StudentApplicationCreateInput,
    student_app_service: StudentApplicationService = Depends(),
):
    # Vérifier si l'utilisateur a déjà une candidature pour cette session
    existing_application = await student_app_service.get_student_application_by_user_id_and_training_session(
        email=input.email, 
        training_session_id=input.target_session_id
    )
    
    if existing_application and existing_application.status not in [ApplicationStatusEnum.APPROVED.value, ApplicationStatusEnum.REFUSED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message="You already have a pending application for this training session",
                error_code="DUPLICATE_APPLICATION"
            ).model_dump(),
        )
    
    # Créer la candidature
    application = await student_app_service.start_student_application(input)
    
    # Get training session for payment details
    training_session = await student_app_service.get_training_session_by_id(input.target_session_id)
    if not training_session:
        await student_app_service.delete_student_application(application)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Training session not found",
                error_code="TRAINING_SESSION_NOT_FOUND"
            ).model_dump(),
        )
    
    # Si paiement par virement bancaire, pas besoin d'initialiser le paiement
    if input.payment_method == "TRANSFER":
        # Vérifier que le reçu de virement est fourni
        submitted_types = [att.type for att in (input.attachments or [])]
        if "BANK_TRANSFER_RECEIPT" not in submitted_types:
            await student_app_service.delete_student_application(application)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message="Bank transfer receipt is required",
                    error_code="ATTACHMENT_REQUIRED"
                ).model_dump(),
            )
        
        return {"message": "Student application created successfully", "data": {
            "student_application": application,
            "payment": None
        }}
    
    # Paiement en ligne (ONLINE) : initialiser le paiement
    from src.api.payments.service import PaymentService
    from src.api.payments.schemas import PaymentInitInput
    import sys
    
    payment_service = PaymentService(student_app_service.session)
    
    payment_input = PaymentInitInput(
        payable=application,
        amount=training_session.registration_fee or 0,
        product_currency=training_session.currency or "XOF",
        description=f"Frais d'inscription à la formation {training_session.training_id}",
        payment_provider="CINETPAY",
        customer_name=input.last_name or "Student",
        customer_surname=input.first_name or "Student",
        customer_email=input.email,
        customer_phone_number=input.phone_number or "0000000000",
        customer_address=input.address or "Address",
        customer_city=input.city or "City",
        customer_country=input.country_code or "SN",
        customer_state=input.country_code or "SN",
        customer_zip_code="00000"
    )
    
    try:
        payment = await payment_service.initiate_payment(payment_input)
    except Exception as e:
        print(e.with_traceback(sys.exc_info()[2]))
        await student_app_service.delete_student_application(application)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message="Payment initiation failed",
                error_code="PAYMENT_INITIATION_FAILED"
            ).model_dump(),
        )
    
    if payment.get("success") is False:
        await student_app_service.delete_student_application(application)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message="Payment initiation failed: " + payment.get("message", ""),
                error_code="PAYMENT_INITIATION_FAILED"
            ).model_dump(),
        )
    
    # Convertir les données de paiement en PaymentInfoOut
    payment_data = payment.get("data", {})
    payment_info = PaymentInfoOut(
        payment_provider=payment_data.get("payment_provider", "CINETPAY"),
        amount=payment_data.get("amount", 0),
        currency=payment_data.get("currency", "XOF"),
        transaction_id=payment_data.get("transaction_id", ""),
        payment_link=payment_data.get("payment_link"),
        notify_url=payment_data.get("notify_url"),
        message=payment_data.get("message")
    )
    
    return {"message": "Student application created successfully", "data": {
        "student_application": application,
        "payment": payment_info
    }}


@router.get("/my-student-applications", response_model=StudentApplicationsPageOutSuccess, tags=["My Student Application"])
async def list_my_student_applications(
    input:   Annotated[StudentApplicationFilter, Query(...)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    student_app_service: StudentApplicationService = Depends(),
):
    
    applications, total = await student_app_service.get_student_application(filters=input, user_id=current_user.id)
    
    
    return {"data": applications, "page": input.page, "number": len(applications), "total_number": total}

@router.get("/my-student-applications/{application_id}", response_model=StudentApplicationOutSuccess, tags=["My Student Application"])
async def get_my_student_application(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    student_app_service: StudentApplicationService = Depends(),
):
    full_application = await student_app_service.get_full_student_application_by_id(application_id=application_id,user_id = current_user.id)
    if full_application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    return {"message": "Student application fetched successfully", "data": full_application}


@router.put("/my-student-applications/{application_id}", response_model=StudentApplicationOutSuccess, tags=["My Student Application"])
async def update_my_student_application(
    application_id: int,
    input: StudentApplicationCreateInput,
    current_user: Annotated[User, Depends(get_current_active_user)],
    student_app_service: StudentApplicationService = Depends(),
):
    """Update a student application by user"""
    # Vérifier que la candidature appartient à l'utilisateur
    existing_application = await student_app_service.get_student_application_by_id(application_id, user_id=current_user.id)
    if existing_application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Student application not found",
                error_code="STUDENT_APPLICATION_NOT_FOUND",
            ).model_dump(),
        )
    
    # Mettre à jour la candidature
    updated_application = await student_app_service.update_student_application_by_id(application_id, input, current_user.id)
    return {"message": "Student application updated successfully", "data": updated_application}

@router.delete("/my-student-applications/{application_id}", response_model=StudentApplicationOutSuccess, tags=["My Student Application"])
async def delete_my_student_application(
    application_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    student_app_service: StudentApplicationService = Depends(),
):
    full_application = await student_app_service.get_full_student_application_by_id(application_id=application_id,user_id = current_user.id)
    if full_application is None or full_application.status == ApplicationStatusEnum.APPROVED.value or full_application.status == ApplicationStatusEnum.REFUSED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    
    await student_app_service.delete_student_application(full_application)
    
    return {"message": "Student application fetched successfully", "data": full_application}

@router.get("/my-student-applications/{application_id}/attachments", response_model=StudentAttachmentListOutSuccess, tags=["My Student Application"])
async def list_student_attachments(
    application_id: int,
    student_app_service: StudentApplicationService = Depends(),
):
    attachments = await student_app_service.list_attachments_by_application(application_id, user_id=None)
    return {"message": "Attachments fetched successfully", "data": attachments}

# Student Attachments
@router.post("/my-student-applications/{application_id}/attachments", response_model=StudentAttachmentOutSuccess, tags=["My Student Application"])
async def create_student_attachment(
    application_id: int,
    input : Annotated[StudentAttachmentInput,Form(...)],
    student_app_service: StudentApplicationService = Depends(),
):
    application = await student_app_service.get_student_application_by_id(application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    attachment = await student_app_service.create_student_attachment(user_id= application.user_id, application_id=application_id, input = input)
    return {"message": "Attachment created successfully", "data": attachment}

@router.delete("/my-student-attachments/{attachment_id}", response_model=StudentAttachmentOutSuccess, tags=["My Student Application"])
async def delete_student_attachment(
    attachment_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    student_app_service: StudentApplicationService = Depends(),
):
    attachment = await student_app_service.get_student_attachment_by_id(attachment_id, user_id=current_user.id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_ATTACHMENT_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_ATTACHMENT_NOT_FOUND.value,
            ).model_dump(),
        )
    attachment = await student_app_service.delete_student_attachment(attachment)
    return {"message": "Attachment deleted successfully", "data": attachment}


@router.post("/my-student-applications/{application_id}/submit", response_model=InitPaymentOutSuccess, tags=["My Student Application"])
async def submit_student_application(
    application_id: int,
    payment_params: PaymentParametersInput = None,
    # current_user: Annotated[User, Depends(get_current_active_user)],
    student_app_service: StudentApplicationService = Depends(),
):
    application = await student_app_service.get_student_application_by_id(application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
        
    
    payment = await student_app_service.submit_student_application(application, payment_params)
    if payment["success"] == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.PAYMENT_INITIATION_FAILED.description + " (" + payment["message"] + ")" ,
                error_code=ErrorMessage.PAYMENT_INITIATION_FAILED.value,
            ).model_dump(),
        )
    return {"message": "Application submitted successfully", "data": payment}


@router.post("/my-student-applications/pay-training-fee", response_model=InitPaymentOutSuccess, tags=["My Student Application"])
async def pay_training_fee(
    input: PayTrainingFeeInstallmentInput,
    current_user: Annotated[User, Depends(get_current_active_user)],
    student_app_service: StudentApplicationService = Depends(),
):
    
    payment = await student_app_service.make_training_installment_fee_payment(user_id=current_user.id, input=input)
    if payment["success"] == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=ErrorMessage.PAYMENT_INITIATION_FAILED.description + " (" + payment["message"] + ")" ,
                error_code=ErrorMessage.PAYMENT_INITIATION_FAILED.value,
            ).model_dump(),
        )
    return {"message": "Application submitted successfully", "data": payment}