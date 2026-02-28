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
            if not payment:
                return {"message": "failed", "data": None}

            if payment.status == PaymentStatusEnum.PENDING.value:
                payment = PaymentService.check_payment_status_sync(session, payment)

            return {"message": "success", "data": payment.model_dump()}

@shared_task
def handle_payment_effects(payment_id: str):
    """
    Background task to handle slow operations after a payment is confirmed.
    - Moodle enrollment
    - Candidate account creation
    - Email notifications
    """
    from src.api.payments.service import PaymentService
    from src.database import get_session
    
    with get_session() as session:
        statement = select(Payment).where(Payment.id == payment_id)
        payment = session.exec(statement).first()
        
        if not payment or payment.status != PaymentStatusEnum.ACCEPTED.value:
            return
            
        if payment.payable_type == "JobApplication":
            from src.api.job_offers.models import JobApplication
            job_app = session.exec(select(JobApplication).where(JobApplication.id == int(payment.payable_id))).first()
            if job_app:
                # We use the sync static method for account creation
                PaymentService._create_job_application_user_sync_static(job_app, session)
                
        elif payment.payable_type == "StudentApplication":
            from src.api.training.models import StudentApplication
            from src.api.training.services.student_application import StudentApplicationService
            student_app = session.exec(select(StudentApplication).where(StudentApplication.id == int(payment.payable_id))).first()
            if student_app:
                # Enroll sync
                training_service = StudentApplicationService(session)
                # We need to make sure we can call this with a sync session if possible, 
                # or adapt the service to work with both.
                # Actually, many services use AsyncSession. 
                # If the service is strictly async, we might need a separate sync handler.
                pass 
                # To be implemented carefully based on service design

