import sys
from typing import List, Optional, Tuple
from datetime import date, datetime, timezone
from fastapi import Depends, HTTPException ,status
from sqlalchemy import func, update 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, or_

from src.api.job_offers.models import ApplicationStatusEnum
from src.database import get_session_async
from src.api.training.models import (
    TrainingFeeInstallmentPayment,
    TrainingSession,
    StudentApplication,
    StudentAttachment,
    TrainingSessionParticipant,
    Training,
)
from src.api.user.models import User
from src.api.training.schemas import (
    ChangeStudentApplicationStatusInput,
    PayTrainingFeeInstallmentInput,
    StudentApplicationCreateInput,
    StudentApplicationFilter,
    StudentAttachmentInput,
    PaymentParametersInput,
)
from src.api.user.service import UserService
from src.api.user.models import User, UserTypeEnum
from src.api.payments.schemas import PaymentInitInput
# Importation différée pour éviter l'importation circulaire
# from src.api.payments.service import PaymentService
from src.config import settings
from src.helper.file_helper import FileHelper
from src.helper.moodle import MoodleService
from src.helper.notifications import SendPasswordNotification
from src.helper.schemas import BaseOutFail, ErrorMessage

try:
    from src.helper.moodle import (
        moodle_create_course_task,
        moodle_ensure_user_task,
        moodle_enrol_user_task,
    )
except Exception:
    moodle_create_course_task = None
    moodle_ensure_user_task = None
    moodle_enrol_user_task = None

import secrets
import string

def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

class StudentApplicationService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    # Student Applications CRUD
    async def start_student_application(self, data: StudentApplicationCreateInput) -> StudentApplication:
        """Create a new student application"""
        user_service = UserService(self.session)

        user = await user_service.get_by_email(data.email)
        
        if user is None:
            # create a user with default password
            default_password = generate_password(8)
            create_input = {
                "first_name": data.first_name or "",
                "last_name": data.last_name or "",
                "country_code": data.country_code or "SN",
                "mobile_number": data.phone_number or "",
                "email": data.email,
                "password": default_password,
                "user_type": UserTypeEnum.STUDENT,
            }
            user = await user_service.create(create_input)
            
            SendPasswordNotification(
                email=data.email,
                name=user.full_name(),
                password=default_password
            ).send_notification()  
            
        session_stmt = select(TrainingSession).where(TrainingSession.id == data.target_session_id)
        session_res = await self.session.execute(session_stmt)
        target_session = session_res.scalars().first()
        
        if target_session is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.TRAINING_SESSION_NOT_FOUND.description,
                    error_code=ErrorMessage.TRAINING_SESSION_NOT_FOUND.value
                ).model_dump()
            )
            
        if target_session.registration_deadline < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.REGISTRATION_CLOSED.description,
                    error_code=ErrorMessage.REGISTRATION_CLOSED.value
                ).model_dump()
            )
            
        if target_session.status != "OPEN_FOR_REGISTRATION":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.SESSION_NOT_OPEN.description,
                    error_code=ErrorMessage.SESSION_NOT_OPEN.value
                ).model_dump()
            )
            
        if target_session.available_slots is not None and target_session.available_slots <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.NO_AVAILABLE_SLOTS.description,
                    error_code=ErrorMessage.NO_AVAILABLE_SLOTS.value
                ).model_dump()
            )

        # Generate application number
        training_id = target_session.training_id
        count_stmt = select(func.count(StudentApplication.id)).where(StudentApplication.training_id == training_id)
        count_res = await self.session.execute(count_stmt)
        seq = (count_res.scalar() or 0) + 1
        application_number = f"APP-TRAIN-{seq:04d}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create application with all fields
        application = StudentApplication(
            user_id=user.id,
            training_id=training_id,
            target_session_id=data.target_session_id,
            application_number=application_number,
            registration_fee=target_session.registration_fee,
            training_fee=target_session.training_fee,
            currency=target_session.currency,
            payment_method=data.payment_method,
            civility=data.civility,
            city=data.city,
            address=data.address,
            date_of_birth=data.date_of_birth,
        )
        
        print(f"📝 [BACKEND] Application created with additional data: payment_method={data.payment_method}, civility={data.civility}, city={data.city}, address={data.address}, date_of_birth={data.date_of_birth}")
        self.session.add(application)
        await self.session.commit()
        await self.session.refresh(application)
        return application
    
    async def update_student_application(self, application: StudentApplication, data) -> StudentApplication:
        """Update student application"""
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(application, key, value)
        self.session.add(application)
        await self.session.commit()
        await self.session.refresh(application)
        return application

    async def update_student_application_by_id(self, application_id: int, data, user_id: str) -> StudentApplication:
        """Update student application by ID and user ID"""
        # Get the application
        application = await self.get_student_application_by_id(application_id, user_id)
        if not application:
            raise ValueError("Student application not found")
        
        # Update the application
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(application, key, value)
        
        application.updated_at = datetime.now(timezone.utc)
        self.session.add(application)
        await self.session.commit()
        await self.session.refresh(application)
        return application

    async def submit_student_application(self, application: StudentApplication, payment_params=None) -> dict:
        """Submit student application and initiate payment"""
        # Use the target session to get fees
        session_stmt = select(TrainingSession).where(TrainingSession.id == application.target_session_id)
        session_res = await self.session.execute(session_stmt)
        target_session = session_res.scalars().first()
        if target_session is None:
            return {"message": "failed", "reason": "SESSION_NOT_FOUND"}

        # Validate required attachments from session
        if target_session.required_attachments:
            existing = await self.list_attachments_by_application(application.id)
            existing_types = {a.document_type for a in existing}
            for required in target_session.required_attachments:
                if required not in existing_types:
                    return {"message": "failed", "reason": f"MISSING_ATTACHMENT:{required}"}

        amount = target_session.registration_fee or 0.0
        
        tr_stmt = select(Training).where(Training.id == target_session.training_id)
        tr_res = await self.session.execute(tr_stmt)
        training = tr_res.scalars().first()
        # Format dates (use only if available)
        start_str = target_session.start_date.strftime("%B %Y") if target_session.start_date else "Undated"
        cohort = f"Cohort {target_session.id[:6].upper()}"  # short unique label

        fullname = f"{training.title} – {start_str} {cohort}"
        
        # Importation différée pour éviter l'importation circulaire
        from src.api.payments.service import PaymentService
        payment_service = PaymentService(self.session)
        
        # Créer le PaymentInitInput avec les paramètres de paiement
        payment_input = PaymentInitInput(
            payable=application,
            amount=amount,
            product_currency=target_session.currency,
            description=f"Frais d'inscription à la formation {fullname}",
            payment_provider="CINETPAY",
        )
        
        # Si des paramètres de paiement sont fournis, les appliquer
        if payment_params:
            print(f"=== PAYMENT PARAMETERS APPLIED ===")
            print(f"Payment Methods: {payment_params.payment_methods}")
            print(f"Enable Card Payments: {payment_params.enable_card_payments}")
            print(f"Enable Bank Transfers: {payment_params.enable_bank_transfers}")
            print(f"Channels: {payment_params.channels}")
            
            # Modifier temporairement la configuration CinetPay pour cette transaction
            # Sauvegarder la configuration originale
            original_channels = settings.CINETPAY_CHANNELS
            
            # Appliquer les nouveaux canaux si fournis
            if payment_params.channels:
                settings.CINETPAY_CHANNELS = payment_params.channels
                print(f"Temporarily changed CINETPAY_CHANNELS to: {settings.CINETPAY_CHANNELS}")
            
            try:
                payment = await payment_service.initiate_payment(payment_input)
            finally:
                # Restaurer la configuration originale
                settings.CINETPAY_CHANNELS = original_channels
                print(f"Restored CINETPAY_CHANNELS to: {settings.CINETPAY_CHANNELS}")
        else:
            try:
                payment = await payment_service.initiate_payment(payment_input)
            except Exception as e:
                print(e.with_traceback(sys.exc_info()[2]))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=BaseOutFail(
                        message=ErrorMessage.PAYMENT_INITIATION_FAILED.description,
                        error_code=ErrorMessage.PAYMENT_INITIATION_FAILED.value,
                    ).model_dump(),
                )
        
        return payment

    async def get_student_application_by_id(self, application_id: int,user_id : Optional[str]=None) -> Optional[StudentApplication]:
        """Get student application by ID"""
        statement = select(StudentApplication).where(StudentApplication.id == application_id, StudentApplication.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def get_student_application_by_user_id_and_training_session(self, email: str, training_session_id: str) -> Optional[StudentApplication]:
        """Get student application by ID"""
        statement = (
            select(StudentApplication).join(User, User.id == StudentApplication.user_id)
            .where(User.email == email)
            .where( StudentApplication.target_session_id == training_session_id,  StudentApplication.delete_at.is_(None)))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_student_application_by_application_number(self, application_number: str,user_id : Optional[str]) -> Optional[StudentApplication]:
        """Get student application by ID"""
        statement = (
            select(StudentApplication)
            .where( StudentApplication.application_number == application_number,  StudentApplication.delete_at.is_(None)))
        
        if user_id :
            statement = statement.where(StudentApplication.user_id ==user_id )
        
        result = await self.session.execute(statement)  
        return result.scalars().first()
    async def get_full_student_application_by_id(self, application_id: int, user_id: Optional[str] = None) -> Optional[StudentApplication]:
        """Get full student application by ID with relationships"""
        statement = (
            select(StudentApplication)
            .where(StudentApplication.id == application_id, StudentApplication.delete_at.is_(None))
            .options(selectinload(StudentApplication.training))
            .options(selectinload(StudentApplication.training_session))
            .options(selectinload(StudentApplication.attachments))
        )
        
        if user_id is not None:
            statement = statement.where(StudentApplication.user_id == user_id)
            
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def get_student_application(self, filters: StudentApplicationFilter, user_id: Optional[str] = None) -> Tuple[List[dict], int]:
        """Get student applications with filtering"""
        statement = (
            select(
                StudentApplication.id,
                StudentApplication.application_number,
                StudentApplication.status,
                StudentApplication.target_session_id,
                StudentApplication.refusal_reason,  
                StudentApplication.registration_fee,
                StudentApplication.training_fee,
                StudentApplication.currency,
                StudentApplication.created_at,
                StudentApplication.updated_at,
                StudentApplication.training_id,
                StudentApplication.payment_id,
                Training.title.label("training_title"),
                TrainingSession.start_date.label("training_session_start_date"),
                TrainingSession.end_date.label("training_session_end_date"),
                StudentApplication.user_id,
                User.email.label("user_email"),
                User.first_name.label("user_first_name"),
                User.last_name.label("user_last_name"),
            )
            .join(User, User.id == StudentApplication.user_id)
            .join(Training, Training.id == StudentApplication.training_id)
            .join(TrainingSession, TrainingSession.id == StudentApplication.target_session_id)
            .where(StudentApplication.delete_at.is_(None))
        )
        
        count_query = (
            select(func.count(StudentApplication.id))
            .join(User, User.id == StudentApplication.user_id)
            .join(Training, Training.id == StudentApplication.training_id)         
            .join(TrainingSession, TrainingSession.id == StudentApplication.target_session_id)
            .where(StudentApplication.delete_at.is_(None))
        )
        
        if user_id is not None:
            statement = statement.where(StudentApplication.user_id == user_id)
            count_query = count_query.where(StudentApplication.user_id == user_id)
        

        if filters.search is not None:
            like_clause = or_(
                User.first_name.contains(filters.search),
                User.last_name.contains(filters.search),
                Training.title.contains(filters.search),
                Training.presentation.contains(filters.search),
            )
            statement = statement.where(like_clause)
            count_query = count_query.where(like_clause)

        if filters.status is not None:
            statement = statement.where(StudentApplication.status == filters.status)
            count_query = count_query.where(StudentApplication.status == filters.status)
            
        if filters.training_id is not None:
            statement = statement.where(StudentApplication.training_id == filters.training_id)
            count_query = count_query.where(StudentApplication.training_id == filters.training_id)
            
        if filters.training_session_id is not None:
            statement = statement.where(StudentApplication.target_session_id == filters.training_session_id)
            count_query = count_query.where(StudentApplication.target_session_id == filters.training_session_id)

        # Filter by payment status
        if filters.is_paid is not None:
            if filters.is_paid:
                # Applications that have a payment_id (paid)
                statement = statement.where(StudentApplication.payment_id.is_not(None))
                count_query = count_query.where(StudentApplication.payment_id.is_not(None))
            else:
                # Applications that don't have a payment_id (not paid)
                statement = statement.where(StudentApplication.payment_id.is_(None))
                count_query = count_query.where(StudentApplication.payment_id.is_(None))

        if filters.order_by == "created_at":
            statement = statement.order_by(StudentApplication.created_at if filters.asc == "asc" else StudentApplication.created_at.desc())

        total_count = (await self.session.execute(count_query)).scalar_one()

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        
        # Convert results to StudentApplicationOut format
        applications = []
        for row in result.all():
            app_data = {
                'id': row.id,
                'user_id': row.user_id,
                'training_id': row.training_id,
                'target_session_id': row.target_session_id,
                'application_number': row.application_number,
                'status': row.status,
                'payment_id': row.payment_id,
                'refusal_reason': row.refusal_reason,
                'registration_fee': float(row.registration_fee) if row.registration_fee else None,
                'training_fee': float(row.training_fee) if row.training_fee else None,
                'currency': row.currency,
                'training_title': row.training_title,
                'training_session_start_date': row.training_session_start_date,
                'training_session_end_date': row.training_session_end_date,
                'user_email': row.user_email,
                'user_first_name': row.user_first_name,
                'user_last_name': row.user_last_name,
                'is_paid': row.payment_id is not None,
                'created_at': row.created_at,
                'updated_at': row.updated_at
            }
            applications.append(app_data)
        
        return applications, total_count
    
    async def get_payment_statistics(self) -> dict:
        """Get payment statistics for student applications"""
        # Total applications
        total_stmt = select(func.count(StudentApplication.id)).where(StudentApplication.delete_at.is_(None))
        total_result = await self.session.execute(total_stmt)
        total_applications = total_result.scalar() or 0
        
        # Paid applications
        paid_stmt = select(func.count(StudentApplication.id)).where(
            StudentApplication.delete_at.is_(None),
            StudentApplication.payment_id.is_not(None)
        )
        paid_result = await self.session.execute(paid_stmt)
        paid_applications = paid_result.scalar() or 0
        
        # Unpaid applications
        unpaid_applications = total_applications - paid_applications
        
        # Total revenue from paid applications
        revenue_stmt = select(func.sum(StudentApplication.registration_fee + StudentApplication.training_fee)).where(
            StudentApplication.delete_at.is_(None),
            StudentApplication.payment_id.is_not(None)
        )
        revenue_result = await self.session.execute(revenue_stmt)
        total_revenue = revenue_result.scalar() or 0.0
        
        return {
            "total_applications": total_applications,
            "paid_applications": paid_applications,
            "unpaid_applications": unpaid_applications,
            "payment_rate": round((paid_applications / total_applications * 100) if total_applications > 0 else 0, 2),
            "total_revenue": float(total_revenue),
            "currency": "EUR"  # Default currency
        }
    
    async def delete_student_application(self, application: StudentApplication) -> StudentApplication:
        """Delete student application"""
        await self.dissociate_student_attachment(application_id=application.id)
        await self.session.delete(application)
        await self.session.commit()
        return application
    
    async def get_training_session_by_id(self, session_id: str) -> Optional[TrainingSession]:
        """Get training session by ID"""
        statement = select(TrainingSession).where(TrainingSession.id == session_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def enroll_student_to_session(self, application: StudentApplication) -> TrainingSessionParticipant:
        """Enroll student to training session"""
        participant = TrainingSessionParticipant(
            session_id=application.target_session_id,
            user_id=application.user_id,
            application_id=application.id,
            joined_at=datetime.now(timezone.utc),
        )
        self.session.add(participant)
        
        # decrement available slots if applicable
        if application.target_session_id is not None:
            stmt = select(TrainingSession).where(TrainingSession.id == application.target_session_id)
            res = await self.session.execute(stmt)
            sess = res.scalars().first()
            if sess and sess.available_slots is not None and sess.available_slots > 0:
                sess.available_slots -= 1
                self.session.add(sess)
        
        await self.session.commit()
        await self.session.refresh(participant)

        # Enrol on Moodle (best-effort)
        
        if sess and sess.moodle_course_id:
                user_service = UserService(self.session)
                user = await user_service.get_by_id(application.user_id)
                if user and user.email:
                    """
                    if moodle_ensure_user_task and moodle_enrol_user_task:
                        moodle_ensure_user_task.apply_async(kwargs={
                            "email": user.email,
                            "firstname": user.first_name,
                            "lastname": user.last_name,
                        })
                    else:
                    
                        moodle = MoodleService()
                        moodle_user_id = user.moodle_user_id
                        if not moodle_user_id:
                            moodle_user_id = await moodle.ensure_user(
                                email=user.email,
                                firstname=user.first_name,
                                lastname=user.last_name,
                            )
                            user.moodle_user_id = moodle_user_id
                            self.session.add(user)
                            await self.session.commit()
                            await self.session.refresh(user)
                        await moodle.enrol_user_manual(user_id=moodle_user_id, course_id=sess.moodle_course_id)
                    """
                    moodle = MoodleService()
                    moodle_user_id = user.moodle_user_id
                    if not moodle_user_id:
                        moodle_user_id = await moodle.ensure_user(
                            email=user.email,
                            firstname=user.first_name,
                            lastname=user.last_name
                        )
                        user.moodle_user_id = moodle_user_id
                        self.session.add(user)
                        await self.session.commit()
                        await self.session.refresh(user)
                    await moodle.enrol_user_manual(user_id=moodle_user_id, course_id=sess.moodle_course_id)
                    

        return participant

    # Attachments
    async def create_student_attachment(self, user_id: str, application_id: int, input: StudentAttachmentInput) -> StudentAttachment:
        """Create student attachment"""
        # Replace existing attachment of same type
        existing_stmt = (
            select(StudentAttachment)
            .join(StudentApplication, StudentApplication.id == StudentAttachment.application_id)
            .where(StudentApplication.user_id == user_id)
            .where(StudentAttachment.document_type == input.name, StudentAttachment.application_id == application_id))
        existing_res = await self.session.execute(existing_stmt)
        existing = existing_res.scalars().first()
        if existing is not None:
            FileHelper.delete_file(existing.file_path)
            await self.session.delete(existing)
            await self.session.commit()

        url, _, _ = await FileHelper.upload_file(input.file, f"/student-applications/{application_id}", input.name)
        attachment = StudentAttachment(application_id=application_id, file_path=url, document_type=input.name)
        self.session.add(attachment)
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment

    async def dissociate_student_attachment(self, application_id: int) -> None:
        """Dissociate student attachment"""
        statement = update(StudentAttachment).where(StudentAttachment.application_id == application_id).values(application_id=None)
        await self.session.execute(statement)
        await self.session.commit()

    async def get_student_attachment_by_id(self, attachment_id: int, user_id: Optional[str] = None) -> Optional[StudentAttachment]:
        """Get student attachment by ID"""
        existing_stmt = (
            select(StudentAttachment)
            .join(StudentApplication, StudentApplication.id == StudentAttachment.application_id)
            .where(StudentAttachment.id == attachment_id))
        if user_id is not None:
            existing_stmt = existing_stmt.where(StudentApplication.user_id == user_id)
        result = await self.session.execute(existing_stmt)
        return result.scalars().first()

    async def list_attachments_by_application(self, application_id: int, user_id: Optional[str] = None) -> List[StudentAttachment]:
        """List attachments by application"""
        statement = (
            select(StudentAttachment)
            .where(StudentAttachment.application_id == application_id, StudentAttachment.delete_at.is_(None))
            .order_by(StudentAttachment.created_at)
        )
        
        if user_id is not None:
            statement = statement.join(StudentApplication).where(StudentApplication.user_id == user_id)
            
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_student_attachment(self, attachment: StudentAttachment) -> StudentAttachment:
        """Delete student attachment"""
        FileHelper.delete_file(attachment.file_path)
        self.session.delete(attachment)
        await self.session.commit()
        return attachment
    
    
    async def change_student_application_status(self, student_application : StudentApplication,input : ChangeStudentApplicationStatusInput):
        student_application.refusal_reason = input.reason
        student_application.status = input.status
        
        await self.session.commit()
        await self.session.refresh(student_application)
        
        if input.status == ApplicationStatusEnum.APPROVED.value:
            await self.enroll_student_to_session(student_application)
        
        return student_application
        
    async def update_student_application_payment(self,application_id: int,payment_id:str):
    
        application = await self.get_student_application_by_id(application_id)
        application.payment_id = payment_id
        self.session.add(application)
        await self.session.commit()
        
        return application
    
    
    async def make_training_installment_fee_payment(self,user_id: str,input:PayTrainingFeeInstallmentInput):
        
        statement = (
            select(StudentApplication).where(StudentApplication.user_id == user_id)
            .where(StudentApplication.target_session_id == input.training_session_id)
            .where(StudentApplication.payment_id != None).where(StudentApplication.delete_at.is_(None))
        )
        result = await self.session.execute(statement)
        registration = result.scalars().first()
        
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.YOU_ARE_NOT_REGISTERED_FOR_THIS_TRAINING_SESSION.description,
                    error_code=ErrorMessage.YOU_ARE_NOT_REGISTERED_FOR_THIS_TRAINING_SESSION.value,
                ).model_dump(),
            )
        
        statement = (
            select(TrainingSession).where(TrainingSession.id == input.training_session_id)
            .where(TrainingSession.delete_at.is_(None))
        )
        result = await self.session.execute(statement)
        training_session = result.scalars().first()
        
        if not training_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.TRAINING_SESSION_NOT_FOUND.description,
                    error_code=ErrorMessage.TRAINING_SESSION_NOT_FOUND.value,
                ).model_dump(),
            )
        
        statement = (
            select(TrainingFeeInstallmentPayment).where(TrainingFeeInstallmentPayment.application_id == registration.id)
            .where(TrainingFeeInstallmentPayment.training_session_id == input.training_session_id)
            .where(TrainingFeeInstallmentPayment.User_id == user_id).where(TrainingFeeInstallmentPayment.payment_id != None)
            .where(Training.delete_at.is_(None))
        )
        result = await self.session.execute(statement)
        payments = result.scalars().all()
        
        installment = training_session.installment_percentage
        
        if installment is None or len(installment)==0:
            installment = [100]
        
        amount_paid = 0
        installment_number = 1
        for payment in payments:
            amount_paid += payment.amount
            installment_number += 1
        
        
        amount_left_to_pay = training_session.training_fee - amount_paid
        
        if amount_left_to_pay <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.TRAINING_FEE_ALREADY_PAID.description,
                    error_code=ErrorMessage.TRAINING_FEE_ALREADY_PAID.value,
                ).model_dump(),
            )
        
        amount_to_pay = training_session.training_fee * (installment[installment_number-1] / 100)
        
        if amount_to_pay > amount_left_to_pay:
            amount_to_pay = amount_left_to_pay
        
        if amount_to_pay < input.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.TRAINING_FEE_INSTALLMENT_AMOUNT_TOO_SMALL.description,
                    error_code=ErrorMessage.TRAINING_FEE_INSTALLMENT_AMOUNT_TOO_SMALL.value,
                ).model_dump(),
            )
        
        if input.amount > amount_left_to_pay:
            input.amount = amount_left_to_pay
        
        
        new_payment = TrainingFeeInstallmentPayment(
            amount=input.amount,
            training_session_id=input.training_session_id,
            application_id=registration.id,
            User_id=user_id,
            installment_number=installment_number,
            rest_to_pay=amount_left_to_pay - input.amount,
            currency=training_session.currency
        )
        self.session.add(new_payment)
        await self.session.commit()
        await self.session.refresh(new_payment)
        
        tr_stmt = select(Training).where(Training.id == training_session.training_id)
        tr_res = await self.session.execute(tr_stmt)
        training = tr_res.scalars().first()
        # Format dates (use only if available)
        start_str = training_session.start_date.strftime("%B %Y") if training_session.start_date else "Undated"
        cohort = f"Cohort {training_session.id[:6].upper()}"  # short unique label

        fullname = f"{training.title} – {start_str} {cohort}"
        
        # Importation différée pour éviter l'importation circulaire
        from src.api.payments.service import PaymentService
        payment_service = PaymentService(self.session)
        payment_input = PaymentInitInput(
            payable=new_payment,
            amount=input.amount,
            product_currency=training_session.currency,
            description=f"Frais de formation pour la formation {fullname}",
            payment_provider="CINETPAY",
        )
        try :
            payment = await payment_service.initiate_payment(payment_input)
            
        except Exception as e:
            print(e.with_traceback(sys.exc_info()[2]))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=BaseOutFail(
                    message=ErrorMessage.PAYMENT_INITIATION_FAILED.description,
                    error_code=ErrorMessage.PAYMENT_INITIATION_FAILED.value,
                ).model_dump(),
            )
        return payment
    