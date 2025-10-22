from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Tuple, Optional
from datetime import datetime, timezone
import uuid
import json

from ..payment.schemas import (
    PaymentCreateInput,
    PaymentUpdateInput,
    PaymentFilter,
    CinetpayWebhookInput,
    PaymentStatusEnum,
    PaymentMethodEnum
)
from ..payment.models import Payment
from ..user.models import User

class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_payments(self, filters: PaymentFilter) -> Tuple[List[Payment], int]:
        """Get payments with filters and pagination"""
        # Base query
        statement = select(Payment).where(Payment.delete_at.is_(None))
        count_query = select(func.count(Payment.id)).where(Payment.delete_at.is_(None))

        # Apply filters
        if filters.status:
            statement = statement.where(Payment.status == filters.status)
            count_query = count_query.where(Payment.status == filters.status)

        if filters.payment_method:
            statement = statement.where(Payment.payment_method == filters.payment_method)

        if filters.user_id:
            statement = statement.where(Payment.user_id == filters.user_id)
            count_query = count_query.where(Payment.user_id == filters.user_id)

        if filters.application_id:
            statement = statement.where(Payment.application_id == filters.application_id)
            count_query = count_query.where(Payment.application_id == filters.application_id)

        if filters.date_from:
            statement = statement.where(Payment.created_at >= filters.date_from)
            count_query = count_query.where(Payment.created_at >= filters.date_from)

        if filters.date_to:
            statement = statement.where(Payment.created_at <= filters.date_to)
            count_query = count_query.where(Payment.created_at <= filters.date_to)

        # Apply ordering
        if filters.order_by == "created_at":
            statement = statement.order_by(
                Payment.created_at if filters.asc == "asc" else Payment.created_at.desc()
            )
        elif filters.order_by == "amount":
            statement = statement.order_by(
                Payment.amount if filters.asc == "asc" else Payment.amount.desc()
            )
        elif filters.order_by == "status":
            statement = statement.order_by(
                Payment.status if filters.asc == "asc" else Payment.status.desc()
            )

        # Get total count
        total_count = (await self.session.execute(count_query)).scalar_one()

        # Apply pagination
        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID"""
        statement = select(Payment).where(
            Payment.id == payment_id,
            Payment.delete_at.is_(None)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_payment_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """Get payment by transaction ID"""
        statement = select(Payment).where(
            Payment.transaction_id == transaction_id,
            Payment.delete_at.is_(None)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_payment(self, payment_data: PaymentCreateInput, user_id: str) -> Payment:
        """Create a new payment"""
        # Generate unique payment and transaction IDs
        payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        
        payment = Payment(
            payment_id=payment_id,
            transaction_id=transaction_id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            status=PaymentStatusEnum.PENDING,
            payment_method=payment_data.payment_method,
            user_id=user_id,
            application_id=payment_data.application_id,
            description=payment_data.description,
            metadata=payment_data.metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def update_payment(self, payment_id: int, payment_data: PaymentUpdateInput) -> Optional[Payment]:
        """Update payment"""
        payment = await self.get_payment_by_id(payment_id)
        if not payment:
            return None

        # Update fields
        if payment_data.status:
            payment.status = payment_data.status
            # Set specific timestamps based on status
            if payment_data.status == PaymentStatusEnum.SUCCESS:
                payment.paid_at = datetime.now(timezone.utc)
            elif payment_data.status == PaymentStatusEnum.FAILED:
                payment.failed_at = datetime.now(timezone.utc)
            elif payment_data.status == PaymentStatusEnum.REFUNDED:
                payment.refunded_at = datetime.now(timezone.utc)

        if payment_data.metadata:
            payment.metadata = payment_data.metadata

        payment.updated_at = datetime.now(timezone.utc)
        
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def delete_payment(self, payment_id: int) -> Optional[Payment]:
        """Soft delete payment"""
        payment = await self.get_payment_by_id(payment_id)
        if not payment:
            return None

        payment.delete_at = datetime.now(timezone.utc)
        payment.updated_at = datetime.now(timezone.utc)
        
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def handle_cinetpay_webhook(self, webhook_data: CinetpayWebhookInput) -> dict:
        """Handle CinetPay webhook notification"""
        try:
            # Find payment by transaction ID
            payment = await self.get_payment_by_transaction_id(webhook_data.cpm_trans_id)
            
            if not payment:
                return {
                    "transaction_id": webhook_data.cpm_trans_id,
                    "status": PaymentStatusEnum.FAILED,
                    "processed": False
                }

            # Update payment status based on CinetPay response
            if webhook_data.cpm_result == "00" and webhook_data.cpm_trans_status == "ACCEPTED":
                payment.status = PaymentStatusEnum.SUCCESS
                payment.paid_at = datetime.now(timezone.utc)
            elif webhook_data.cpm_result == "01":
                payment.status = PaymentStatusEnum.FAILED
                payment.failed_at = datetime.now(timezone.utc)
            elif webhook_data.cpm_result == "02":
                payment.status = PaymentStatusEnum.CANCELLED

            # Update metadata with webhook data
            payment.metadata = {
                **payment.metadata,
                "cinetpay_webhook": {
                    "cpm_payid": webhook_data.cpm_payid,
                    "cpm_payment_date": webhook_data.cpm_payment_date,
                    "cpm_payment_time": webhook_data.cpm_payment_time,
                    "cpm_error_message": webhook_data.cpm_error_message,
                    "cpm_phone_number": webhook_data.cpm_phone_number,
                    "cpm_designation": webhook_data.cpm_designation,
                    "cpm_custom": webhook_data.cpm_custom,
                    "cpm_signature": webhook_data.cpm_signature,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
            }

            payment.updated_at = datetime.now(timezone.utc)
            
            self.session.add(payment)
            await self.session.commit()
            await self.session.refresh(payment)

            return {
                "transaction_id": payment.transaction_id,
                "status": payment.status,
                "processed": True
            }

        except Exception as e:
            # Log error and return failure
            print(f"Error processing CinetPay webhook: {str(e)}")
            return {
                "transaction_id": webhook_data.cpm_trans_id,
                "status": PaymentStatusEnum.FAILED,
                "processed": False
            }
