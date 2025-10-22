from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List
from sqlalchemy.ext.asyncio import AsyncSession

from ..user.dependencies import get_current_active_user, check_permissions
from ..user.models import User
from ..user.enums import PermissionEnum
from ..database import get_session_async
from ..base.schemas import BaseOutSuccess, BaseOutFail
from .schemas import (
    PaymentCreateInput,
    PaymentUpdateInput,
    PaymentFilter,
    PaymentStatusCheckInput,
    CinetpayWebhookInput,
    PaymentOut,
    PaymentListOut,
    PaymentStatusOut,
    CinetpayWebhookOut
)
from .services import PaymentService

router = APIRouter()

# Dependencies
async def get_payment_service(session: AsyncSession = Depends(get_session_async)) -> PaymentService:
    return PaymentService(session)

# Payment Endpoints
@router.get("/payments", response_model=PaymentListOut, tags=["Payments"])
async def get_payments(
    filters: PaymentFilter = Depends(),
    current_user: Annotated[User, Depends(get_current_active_user)],
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Get all payments with filters"""
    payments, total_count = await payment_service.get_payments(filters)
    return {
        "success": True,
        "message": "Payments retrieved successfully",
        "data": payments,
        "page": filters.page,
        "number": len(payments),
        "total_number": total_count
    }

@router.get("/payments/{payment_id}", response_model=PaymentOut, tags=["Payments"])
async def get_payment(
    payment_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Get payment by ID"""
    payment = await payment_service.get_payment_by_id(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Payment not found",
                error_code="PAYMENT_NOT_FOUND",
            ).model_dump(),
        )
    
    return {
        "success": True,
        "message": "Payment retrieved successfully",
        "data": payment
    }

@router.get("/payments-by-transaction/{transaction_id}", response_model=PaymentStatusOut, tags=["Payments"])
async def get_payment_by_transaction(
    transaction_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Get payment by transaction ID"""
    payment = await payment_service.get_payment_by_transaction_id(transaction_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Payment not found",
                error_code="PAYMENT_NOT_FOUND",
            ).model_dump(),
        )
    
    return {
        "success": True,
        "message": "Payment retrieved successfully",
        "data": {
            "transaction_id": payment.transaction_id,
            "status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at
        }
    }

@router.get("/check-status/{transaction_id}", response_model=PaymentStatusOut, tags=["Payments"])
async def check_payment_status(
    transaction_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Check payment status by transaction ID"""
    payment = await payment_service.get_payment_by_transaction_id(transaction_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Payment not found",
                error_code="PAYMENT_NOT_FOUND",
            ).model_dump(),
        )
    
    return {
        "success": True,
        "message": "Payment status retrieved successfully",
        "data": {
            "transaction_id": payment.transaction_id,
            "status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at
        }
    }

@router.post("/payments", response_model=PaymentOut, tags=["Payments"])
async def create_payment(
    payment_data: PaymentCreateInput,
    current_user: Annotated[User, Depends(get_current_active_user)],
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Create a new payment"""
    payment = await payment_service.create_payment(payment_data, current_user.id)
    return {
        "success": True,
        "message": "Payment created successfully",
        "data": payment
    }

@router.put("/payments/{payment_id}", response_model=PaymentOut, tags=["Payments"])
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdateInput,
    current_user: Annotated[User, Depends(get_current_active_user)],
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Update payment"""
    payment = await payment_service.update_payment(payment_id, payment_data)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Payment not found",
                error_code="PAYMENT_NOT_FOUND",
            ).model_dump(),
        )
    
    return {
        "success": True,
        "message": "Payment updated successfully",
        "data": payment
    }

@router.delete("/payments/{payment_id}", response_model=PaymentOut, tags=["Payments"])
async def delete_payment(
    payment_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    payment_service: PaymentService = Depends(get_payment_service),
):
    """Delete payment (soft delete)"""
    payment = await payment_service.delete_payment(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BaseOutFail(
                message="Payment not found",
                error_code="PAYMENT_NOT_FOUND",
            ).model_dump(),
        )
    
    return {
        "success": True,
        "message": "Payment deleted successfully",
        "data": payment
    }

@router.post("/cinetpay/notify", response_model=CinetpayWebhookOut, tags=["Payments"])
async def cinetpay_webhook(
    webhook_data: CinetpayWebhookInput,
    payment_service: PaymentService = Depends(get_payment_service),
):
    """CinetPay webhook handler"""
    try:
        result = await payment_service.handle_cinetpay_webhook(webhook_data)
        return {
            "success": True,
            "message": "Webhook processed successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                message=f"Webhook processing failed: {str(e)}",
                error_code="WEBHOOK_PROCESSING_FAILED",
            ).model_dump(),
        )
