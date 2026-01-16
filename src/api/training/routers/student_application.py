from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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
    StudentAttachmentOutSuccess,
    StudentAttachmentListOutSuccess,
    StudentApplicationFullOut,
    PaymentInfo,
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
    # Sérialiser avec Pydantic pour inclure les attachements
    from src.api.training.schemas import StudentApplicationFullOut, StudentAttachmentOut
    data = StudentApplicationFullOut.model_validate(full_application, from_attributes=True)
    # Convertir les attachements si présents
    if full_application.attachments:
        data.attachments = [
            StudentAttachmentOut(
                id=att.id,
                application_id=att.application_id,
                document_type=att.document_type,
                file_path=att.file_path,
                created_at=att.created_at,
                updated_at=att.updated_at
            )
            for att in full_application.attachments
        ]
    return {"message": "Student application fetched successfully", "data": data}

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


@router.delete("/student-applications/{application_id}", response_model=StudentApplicationOutSuccess, tags=["Student Application"])
async def delete_student_application_admin(
    application_id: int,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_STUDENT_APPLICATION]))],
    student_app_service: StudentApplicationService = Depends(),
):
    """Delete a student application by ID (Admin only)"""
    application = await student_app_service.get_student_application_by_id(application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.description,
                error_code=ErrorMessage.STUDENT_APPLICATION_NOT_FOUND.value,
            ).model_dump(),
        )
    
    deleted_application = await student_app_service.delete_student_application(application)
    return {"message": "Student application deleted successfully", "data": deleted_application}

#eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YjczZjQ0Mi01NzVhLTQzNzgtODQ3Ny00MTUxMmU1ZjI5Y2MiLCJleHAiOjE3NTg1MTgzMjB9.S99P8yGi6fmN9LTONAm266a2GKW3uvEh54FVitbY6-k

#My  Student Applications
@router.post(
    "/student-applications",
    response_model=StudentApplicationOutSuccess,  # adapte si nom different
    tags=["My Student Application"]
)
async def create_student_application(
    input: StudentApplicationCreateInput,  # schéma d'entrée (email, payment_method, attachments...)
    student_app_service: StudentApplicationService = Depends(),
):
    """
    Crée une candidature étudiante et (si ONLINE) initie un paiement en ligne.
    Retourne la candidature complète + bloc 'payment' (ou null si pas de paiement).
    """

    # 1️⃣ Vérifier s'il existe déjà une candidature pour cet utilisateur et cette session
    application = await student_app_service.get_student_application_by_user_id_and_training_session(
        email=input.email,
        training_session_id=input.target_session_id
    )

    if application is None or application.status in [
        ApplicationStatusEnum.APPROVED.value,
        ApplicationStatusEnum.REFUSED.value
    ]:
        # Démarrer une nouvelle candidature
        application = await student_app_service.start_student_application(input)
    
    # 2️⃣ Recharger la candidature complète (relations incluses)
    application = await student_app_service.get_full_student_application_by_id(
        application.id,
        user_id=application.user_id
    )

    # 3️⃣ Cas TRANSFER → Pas de paiement en ligne, juste retourner la candidature
    # L'utilisateur devra uploader le reçu bancaire via l'endpoint d'attachments
    if getattr(input, "payment_method", None) == "TRANSFER":
        # Envoi mail de confirmation (optionnel) - TODO: Implémenter cette méthode
        # await student_app_service.send_application_confirmation_email(application)

        data_model = StudentApplicationFullOut.model_validate(application, from_attributes=True)
        # Convertir les attachements si présents
        if application.attachments:
            from src.api.training.schemas import StudentAttachmentOut
            data_model.attachments = [
                StudentAttachmentOut(
                    id=att.id,
                    application_id=att.application_id,
                    document_type=att.document_type,
                    file_path=att.file_path,
                    created_at=att.created_at,
                    updated_at=att.updated_at
                )
                for att in application.attachments
            ]
        data = data_model.model_dump()
        data["payment"] = None

        return {
            "success": True,
            "message": "Student application created successfully. Please upload the bank transfer receipt.",
            "data": data
        }

    # 4️⃣ Cas ONLINE → initier paiement via le service
    payment = None
    if getattr(input, "payment_method", None) == "ONLINE":
        payment_obj = await student_app_service.initiate_online_payment(application)

        # --- Construire l'objet PaymentInfo proprement ---
        payment_info = PaymentInfo(
            success=payment_obj.get("success", False),
            payment_provider=payment_obj.get("payment_provider"),
            amount=payment_obj.get("amount"),
            payment_link=payment_obj.get("payment_link"),
            transaction_id=payment_obj.get("transaction_id"),
            notify_url=payment_obj.get("notify_url"),
            message=payment_obj.get("message"),
            raw_response=payment_obj,
            metadata={"application_id": getattr(application, "id", None), "user_email": getattr(application, "email", None)}
        )

        # debug lisible dans logs (JSON)
        print("DEBUG payment_info:", payment_info.model_dump_json(indent=2))

        # Si payment_info.success est True, on prépare le bloc à renvoyer
        if payment_info.success:
            payment = payment_info.model_dump()

            # Optionnel: sauvegarder l'identifiant/URL de paiement dans la candidature
            # (adapter les noms de colonnes à ton modèle ORM)
            try:
                application.payment_provider = payment_info.payment_provider
                application.transaction_id = payment_info.transaction_id
                application.payment_url = str(payment_info.payment_link) if payment_info.payment_link else None
                application.payment_status = payment_info.status
                # si tu as un champ payment_id numérique ou UUID, remplis-le aussi
                # application.payment_id = payment_info.transaction_id
                await student_app_service.save(application)
            except Exception as e:
                # Ne bloque pas le retour au frontend si la sauvegarde échoue, mais logge l'erreur
                print("WARN: unable to persist payment info to application:", e)

        else:
            # paiement non réussi côté provider -> log et renvoyer erreur HTTP si tu veux
            print("WARN: payment initiation failed:", payment_info.model_dump())
            # tu peux choisir de lever une exception à ce stade. Ici on continue et renvoie payment = None

    # 5️⃣ Construire la réponse finale avec la candidature complète + payment
    from src.api.training.schemas import StudentAttachmentOut
    data_model = StudentApplicationFullOut.model_validate(application, from_attributes=True)
    # Convertir les attachements si présents
    if application.attachments:
        data_model.attachments = [
            StudentAttachmentOut(
                id=att.id,
                application_id=att.application_id,
                document_type=att.document_type,
                file_path=att.file_path,
                created_at=att.created_at,
                updated_at=att.updated_at
            )
            for att in application.attachments
        ]
    data = data_model.model_dump()
    data["payment"] = payment

    # Optionnel: envoyer l'email de confirmation même si paiement ONLINE (selon ton besoin)
    # await student_app_service.send_application_confirmation_email(application)

    return {
        "success": True,
        "message": "Student application created successfully",
        "data": data
    }


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
    # Sérialiser avec Pydantic pour inclure les attachements
    from src.api.training.schemas import StudentApplicationFullOut, StudentAttachmentOut
    data = StudentApplicationFullOut.model_validate(full_application, from_attributes=True)
    # Convertir les attachements si présents
    if full_application.attachments:
        data.attachments = [
            StudentAttachmentOut(
                id=att.id,
                application_id=att.application_id,
                document_type=att.document_type,
                file_path=att.file_path,
                created_at=att.created_at,
                updated_at=att.updated_at
            )
            for att in full_application.attachments
        ]
    return {"message": "Student application fetched successfully", "data": data}


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
    name: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
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
    
    # Créer un objet input pour le service
    from src.api.training.schemas import StudentAttachmentInput
    input_data = StudentAttachmentInput(name=name, file=file)
    
    attachment = await student_app_service.create_student_attachment(
        user_id=application.user_id, 
        application_id=application_id, 
        input=input_data
    )
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
        
    
    payment = await student_app_service.submit_student_application(application)
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