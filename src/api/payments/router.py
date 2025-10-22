import hashlib
import hmac
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Header,Query
from src.api.auth.utils import check_permissions
from src.api.payments.dependencies import get_payment_by_transaction
from src.api.payments.models import PaymentStatusEnum
from src.api.payments.service import PaymentService 
from src.api.payments.schemas import  PaymentFilter, PaymentOutSuccess, PaymentPageOutSuccess, WebhookPayload
from src.api.auth.models import User
from src.api.payments.utils import check_cash_in_status
from src.api.user.models import PermissionEnum
from src.config import settings
# This is a placeholder for your actual dependency to get the current user
# You should replace it with your actual implementation.
async def get_current_active_user() -> User:
    # In a real application, you would get the user from the request's
    # authentication credentials (e.g., a JWT token).
    # For this example, we'll return a dummy user.
    return User(id="user123", email="user@example.com", is_active=True)


router = APIRouter()


@router.get("/payments",response_model=PaymentPageOutSuccess)
async def get_payment_status(
    filters: Annotated[PaymentFilter, Query(...)],
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_PAYMENT]))],
    payment_service: PaymentService = Depends()
):
 
    payments, total =await payment_service.list_payments(filters)
    return {"data": payments, "page": filters.page, "number": len(payments), "total_number": total}

@router.get("/payments/{payment_id}",response_model=PaymentOutSuccess)
async def get_payment_status(
    payment_id : str,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_PAYMENT]))],
    payment_service: PaymentService = Depends()
):

    payment =await payment_service.get_payment_by_id(payment_id=payment_id, )
    return {
        "message":"Payment Fetched Successfully",
        "data": payment
    }

@router.get("/payments-by-transaction/{transaction_id}",response_model=PaymentOutSuccess)
async def get_payment_status(
    transaction_id : str,
    current_user: Annotated[User, Depends(check_permissions([PermissionEnum.CAN_VIEW_PAYMENT]))],
    payment_service: PaymentService = Depends()
):
 
    payment =await payment_service.get_payment_by_transaction_id(transaction_id=transaction_id, )
    return {
        "message":"Payment Fetched Successfully",
        "data": payment
    }

@router.post("/cinetpay/notify")
async def cinetpay_webhook_handler(
    cpm_site_id: str = Form(...),
    cpm_trans_id: str = Form(...),
    cpm_trans_date: str = Form(...),
    cpm_amount: str = Form(...),
    cpm_currency: str = Form(...),
    signature: str = Form(...),
    payment_method: str = Form(...),
    cel_phone_num: Optional[str] = Form(None),
    cpm_phone_prefixe: Optional[str] = Form(None),
    cpm_language: Optional[str] = Form(None),
    cpm_version: Optional[str] = Form(None),
    cpm_payment_config: Optional[str] = Form(None),
    cpm_page_action: Optional[str] = Form(None),
    cpm_custom: Optional[str] = Form(None),
    cpm_designation: Optional[str] = Form(None),
    cpm_error_message: Optional[str] = Form(None),
    x_token: str = Header(..., alias="x-token"),
):
    """
    Webhook de notification CinetPay
    """

    # 1️⃣ Construire la chaîne à hasher
    fields = [
        cpm_site_id,
        cpm_trans_id,
        cpm_trans_date,
        cpm_amount,
        cpm_currency,
        signature,
        payment_method,
        cel_phone_num or "",
        cpm_phone_prefixe or "",
        cpm_language or "",
        cpm_version or "",
        cpm_payment_config or "",
        cpm_page_action or "",
        cpm_custom or "",
        cpm_designation or "",
        cpm_error_message or "",
    ]

    data_string = "".join(fields)

    # 2️⃣ Générer le token HMAC
    generated_token = hmac.new(
        settings.CINETPAY_SECRET_KEY.encode("utf-8"),
        data_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # 3️⃣ Vérification de l’intégrité
    if not hmac.compare_digest(x_token, generated_token):
        raise HTTPException(status_code=403, detail="Invalid token")

    # 4️⃣ Déclencher la vérification transactionnelle
    check_cash_in_status.apply_async(
        kwargs={"transaction_id": cpm_trans_id},
        countdown=0
    )
    
    print("Transaction ID",cpm_trans_id)

    # 5️⃣ Répondre avec succès (200 OK attendu par CinetPay)
    return {"ok": True}

@router.get("/check-status/{transaction_id}",response_model=PaymentOutSuccess)
async def get_payment_status(
    transaction_id: str,
    payment : Annotated[User, Depends(get_payment_by_transaction)],
    payment_service: PaymentService = Depends()
):
    if payment.status == PaymentStatusEnum.PENDING.value:
        
        payment = await payment_service.check_payment_status(payment)
        
    return {
        "message" : "success",
        "data": payment
    }

