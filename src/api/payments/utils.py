from celery import shared_task
from sqlalchemy import select

from src.api.payments.models import Payment, PaymentStatusEnum
from src.api.payments.service import PaymentService
from src.database import get_session


@shared_task
def check_cash_in_status(transaction_id: str) -> dict:
    """
    Celery task to check cash-in status for a payment.
    """

    with get_session() as session:
            payment_statement = select(Payment).where(Payment.transaction_id == transaction_id)
            payment = session.scalars(payment_statement).first()
            print(payment.model_dump())
            
            if not payment:
                print("Payment not found")
                return {"message": "failed", "data": None}

            if payment.status == PaymentStatusEnum.PENDING.value:
                print("Payment is pending")
                payment = PaymentService.check_payment_status_sync(session, payment)

            return {"message": "success", "data": payment.model_dump()}
    # ✅ Correctly wrap the async function

