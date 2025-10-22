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


#eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YjczZjQ0Mi01NzVhLTQzNzgtODQ3Ny00MTUxMmU1ZjI5Y2MiLCJleHAiOjE3NTg1MTgzMjB9.S99P8yGi6fmN9LTONAm266a2GKW3uvEh54FVitbY6-k

#My  Student Applications
@router.post("/student-applications", response_model=StudentApplicationWithPaymentOutSuccess, tags=["My Student Application"])
async def create_student_application(
    input: StudentApplicationCreateInput,
    student_app_service: StudentApplicationService = Depends(),
):
    try:
        print(f"📤 [BACKEND] Creating student application for email: {input.email}")
        print(f"📤 [BACKEND] Target session: {input.target_session_id}")
        print(f"📤 [BACKEND] Payment method: {input.payment_method}")
        
        application = await student_app_service.get_student_application_by_user_id_and_training_session(email=input.email, training_session_id=input.target_session_id)
        if application is  None or application.status == ApplicationStatusEnum.APPROVED.value or application.status == ApplicationStatusEnum.REFUSED.value: 
            print(f"📤 [BACKEND] Creating new application...")
            application = await student_app_service.start_student_application(input)
            print(f"📤 [BACKEND] Application created with ID: {application.id}")
        else:
            print(f"📤 [BACKEND] Using existing application ID: {application.id}")
        
        # Get full application details
        full_application = await student_app_service.get_full_student_application_by_id(application.id, user_id=application.user_id)
        print(f"📤 [BACKEND] Full application retrieved: {full_application}")
        
        # Initialize payment if needed
        payment_info = None
        if input.payment_method == "ONLINE":
            print(f"📤 [BACKEND] Initializing online payment...")
            # Initialize online payment
            payment_info = await student_app_service.initialize_payment_for_application(application, input.payment_method)
            print(f"📤 [BACKEND] Payment info: {payment_info}")
        
        # Prepare response data
        response_data = {
            "student_application": full_application,
            "payment": payment_info
        }
        
        print(f"📤 [BACKEND] Returning response: {response_data}")
        return {"message": "Student application created successfully", "data": response_data}
        
    except Exception as e:
        print(f"❌ [BACKEND] Error creating student application: {e}")
        print(f"❌ [BACKEND] Error type: {type(e)}")
        import traceback
        print(f"❌ [BACKEND] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=BaseOutFail(
                message=f"Error creating student application: {str(e)}",
                error_code="STUDENT_APPLICATION_CREATION_FAILED"
            ).model_dump()
        )


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