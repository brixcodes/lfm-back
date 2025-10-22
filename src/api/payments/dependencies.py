from fastapi import Depends, HTTPException ,status
from src.api.payments.service import PaymentService
from src.helper.schemas import BaseOutFail, ErrorMessage


async def get_payment_by_transaction(transaction_id: str, payment_service: PaymentService = Depends(),):
    
    payment = await payment_service.get_payment_by_transaction_id(transaction_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=BaseOutFail(
                    message=ErrorMessage.PAYMENT_NOT_FOUND.description,
                    error_code= ErrorMessage.PAYMENT_NOT_FOUND.value
                ).model_dump()
        )
    return payment
