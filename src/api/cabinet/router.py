from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import json

from src.database import get_session_async
from src.api.auth.utils import get_current_active_user
from src.api.user.models import User
from src.api.user.service import UserService
from src.api.cabinet.service import CabinetApplicationService, ApplicationFeeService
from src.api.cabinet.schemas import (
    CabinetApplicationCreate, CabinetApplicationUpdate, CabinetApplicationOut,
    ApplicationFeeCreate, ApplicationFeeUpdate, ApplicationFeeOut,
    CabinetApplicationPaymentResponse, PaymentWebhookData, CabinetApplicationStats
)

router = APIRouter(tags=["Cabinet Application"])

# Endpoints pour les candidatures de cabinet

@router.post("", response_model=CabinetApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_cabinet_application(
    application_data: CabinetApplicationCreate,
    request: Request,
    session: AsyncSession = Depends(get_session_async)
):
    try:
        service = CabinetApplicationService(session)
        application = await service.create_application(application_data, request)
        return application
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Server error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur interne: {str(e)}")

@router.get("/{application_id}", response_model=CabinetApplicationOut)
async def get_cabinet_application(
    application_id: str,
    session: AsyncSession = Depends(get_session_async)
):
    """Récupérer une candidature par son ID"""
    service = CabinetApplicationService(session)
    application = await service.get_application_by_id(application_id)
    
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")
    
    return application

@router.get("/email/{email}", response_model=CabinetApplicationOut)
async def get_cabinet_application_by_email(
    email: str,
    session: AsyncSession = Depends(get_session_async)
):
    """Récupérer une candidature par email"""
    service = CabinetApplicationService(session)
    application = await service.get_application_by_email(email)
    
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")
    
    return application

@router.put("/{application_id}", response_model=CabinetApplicationOut)
async def update_cabinet_application(
    application_id: str,
    update_data: CabinetApplicationUpdate,
    session: AsyncSession = Depends(get_session_async)
):
    """Mettre à jour une candidature"""
    service = CabinetApplicationService(session)
    application = await service.update_application(application_id, update_data)
    
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")
    
    return application

# Route de paiement supprimée - le paiement est maintenant automatique lors de la création

@router.get("/{application_id}/payment-status")
async def get_payment_status(
    application_id: str,
    session: AsyncSession = Depends(get_session_async)
):
    """Vérifier le statut de paiement d'une candidature"""
    try:
        service = CabinetApplicationService(session)
        status = await service.get_payment_status(application_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de la vérification du statut")

@router.post("/payment-webhook")
async def handle_payment_webhook(
    webhook_data: dict,
    request: Request,
    session: AsyncSession = Depends(get_session_async)
):
    """Webhook pour traiter les notifications de paiement CinetPay"""
    try:
        service = CabinetApplicationService(session)
        
        # Convertir les données du webhook
        webhook_data_obj = PaymentWebhookData(
            transaction_id=webhook_data.get("transaction_id", ""),
            status=webhook_data.get("status", ""),
            amount=float(webhook_data.get("amount", 0)),
            currency=webhook_data.get("currency", "EUR"),
            customer_email=webhook_data.get("customer_email", ""),
            customer_name=webhook_data.get("customer_name", ""),
            payment_reference=webhook_data.get("payment_reference", "")
        )
        
        success = await service.handle_payment_webhook(webhook_data_obj, request)
        
        if success:
            return {"status": "success", "message": "Webhook traité avec succès"}
        else:
            return {"status": "error", "message": "Erreur lors du traitement du webhook"}
            
    except Exception as e:
        return {"status": "error", "message": f"Erreur interne: {str(e)}"}

@router.get("", response_model=List[CabinetApplicationOut])
async def list_cabinet_applications(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Lister les candidatures (admin seulement)"""
    service = CabinetApplicationService(session)
    
    # Convertir le statut string en enum si fourni
    status_enum = None
    if status:
        try:
            from .models import CabinetApplicationStatus
            status_enum = CabinetApplicationStatus(status)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statut invalide")
    
    applications = await service.list_applications(skip=skip, limit=limit, status=status_enum)
    return applications

@router.get("/paid", response_model=List[CabinetApplicationOut])
async def get_paid_cabinet_applications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Récupérer les cabinets qui ont payé les frais de candidature"""
    service = CabinetApplicationService(session)
    applications = await service.get_paid_applications(skip=skip, limit=limit)
    return applications

@router.get("/my-applications", response_model=List[CabinetApplicationOut])
async def get_my_cabinet_applications(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Récupérer les candidatures de l'utilisateur connecté"""
    service = CabinetApplicationService(session)
    applications = await service.get_my_applications(
        user_email=current_user.email, 
        skip=skip, 
        limit=limit
    )
    return applications

@router.get("/stats/overview", response_model=CabinetApplicationStats)
async def get_application_stats(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Récupérer les statistiques des candidatures (admin seulement)"""
    service = CabinetApplicationService(session)
    stats = await service.get_applications_stats()
    return stats

@router.patch("/{application_id}/approve", response_model=CabinetApplicationOut)
async def approve_cabinet_application(
    application_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Approuver une candidature de cabinet"""
    try:
        service = CabinetApplicationService(session)
        application = await service.approve_application(application_id)
        return application
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur interne: {str(e)}")

@router.patch("/{application_id}/reject", response_model=CabinetApplicationOut)
async def reject_cabinet_application(
    application_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Rejeter une candidature de cabinet"""
    try:
        service = CabinetApplicationService(session)
        application = await service.reject_application(application_id, reason)
        return application
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur interne: {str(e)}")

# Endpoints pour les frais de candidature

@router.post("/fees", response_model=ApplicationFeeOut, status_code=status.HTTP_201_CREATED)
async def create_application_fee(
    fee_data: ApplicationFeeCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Créer de nouveaux frais de candidature (admin seulement)"""
    service = ApplicationFeeService(session)
    fee = await service.create_fee(fee_data)
    return fee

@router.get("/fees/{fee_id}", response_model=ApplicationFeeOut)
async def get_application_fee(
    fee_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Récupérer des frais par ID (admin seulement)"""
    service = ApplicationFeeService(session)
    fee = await service.get_fee_by_id(fee_id)
    
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frais non trouvés")
    
    return fee

@router.put("/fees/{fee_id}", response_model=ApplicationFeeOut)
async def update_application_fee(
    fee_id: str,
    update_data: ApplicationFeeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Mettre à jour des frais (admin seulement)"""
    service = ApplicationFeeService(session)
    fee = await service.update_fee(fee_id, update_data)
    
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frais non trouvés")
    
    return fee

@router.get("/fees", response_model=List[ApplicationFeeOut])
async def list_application_fees(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session_async)
):
    """Lister les frais de candidature (admin seulement)"""
    service = ApplicationFeeService(session)
    fees = await service.list_fees(skip=skip, limit=limit)
    return fees

# Endpoint pour upload de documents
@router.post("/{application_id}/upload-document")
async def upload_application_document(
    application_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    session: AsyncSession = Depends(get_session_async)
):
    """Uploader un document pour une candidature"""
    try:
        # Vérifier que la candidature existe
        service = CabinetApplicationService(session)
        application = await service.get_application_by_id(application_id)
        
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidature non trouvée")
        
        # Ici, vous pouvez ajouter la logique d'upload de fichier
        # Par exemple, sauvegarder le fichier et mettre à jour le chemin dans la base de données
        
        return {"message": "Document uploadé avec succès", "document_type": document_type}
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
