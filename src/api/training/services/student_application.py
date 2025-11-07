import sys
from typing import List, Optional, Tuple
from datetime import date, datetime, timezone
from fastapi import Depends, HTTPException ,status
from sqlalchemy import func, update 
from sqlalchemy import  and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload , joinedload
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
from src.api.training.schemas import (
    ChangeStudentApplicationStatusInput,
    PayTrainingFeeInstallmentInput,
    StudentApplicationCreateInput,
    StudentApplicationFilter,
    StudentAttachmentInput,
    StudentApplicationOut,
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
                "country_code": data.country_code or "CM",
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

        application = StudentApplication(
            user_id=user.id,
            training_id=training_id,
            target_session_id=data.target_session_id,
            application_number=application_number,
            registration_fee=target_session.registration_fee,
            training_fee=target_session.training_fee,
            currency=target_session.currency,
            payment_method=getattr(data, 'payment_method', None),
        )
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

    async def submit_student_application(self, application: StudentApplication) -> dict:
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
        payment_input = PaymentInitInput(
            payable=application,
            amount=amount,
            product_currency=target_session.currency,
            description=f"Payment for training application fee of session {fullname}",
            payment_provider="CINETPAY",
            payment_method="WALLET",  # Méthode par défaut pour les formations
            subscription_type="FORMATION",
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

    async def initiate_online_payment(self, application: StudentApplication) -> dict:
        session_stmt = select(TrainingSession).where(TrainingSession.id == application.target_session_id)
        session_res = await self.session.execute(session_stmt)
        target_session = session_res.scalars().first()
        if target_session is None:
            return {"success": False, "message": "SESSION_NOT_FOUND"}

        amount = target_session.registration_fee or 0.0

        tr_stmt = select(Training).where(Training.id == target_session.training_id)
        tr_res = await self.session.execute(tr_stmt)
        training = tr_res.scalars().first()
        start_str = target_session.start_date.strftime("%B %Y") if target_session.start_date else "Undated"
        cohort = f"Cohort {target_session.id[:6].upper()}"
        fullname = f"{training.title} – {start_str} {cohort}"

        from src.api.payments.service import PaymentService
        payment_service = PaymentService(self.session)
        payment_input = PaymentInitInput(
            payable=application,
            amount=amount,
            product_currency=target_session.currency,
            description=f"Payment for training application fee of session {fullname}",
            payment_provider="CINETPAY",
            payment_method="ONLINE",
            subscription_type="FORMATION",
        )
        try:
            payment = await payment_service.initiate_payment(payment_input)
            return payment
        except Exception as e:
            print(e.with_traceback(sys.exc_info()[2]))
            return {"success": False, "message": str(e)}

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
    
    async def get_student_application(self, filters: StudentApplicationFilter, user_id: Optional[str] = None) -> Tuple[List[StudentApplicationOut], int]:
        """Get student applications with filtering"""
        statement = (
            select(StudentApplication)
            .join(User, User.id == StudentApplication.user_id)
            .join(Training, Training.id == StudentApplication.training_id)
            .join(TrainingSession, TrainingSession.id == StudentApplication.target_session_id)
            .where(StudentApplication.delete_at.is_(None))
            .options(joinedload(StudentApplication.training))  # AJOUT : Eager loading pour éviter lazy load
            .options(joinedload(StudentApplication.training_session))
            .options(joinedload(StudentApplication.user))
            .options(selectinload(StudentApplication.attachments))
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

        # Filtrage par paiement basé sur payment_method
        payment_filter = filters.is_paid if filters.is_paid is not None else None
        if payment_filter is not None:
            if payment_filter:
                # "Paid": TRANSFER (tous) OU (ONLINE ET payment_id NOT NULL)
                paid_condition = or_(
                    StudentApplication.payment_method == "TRANSFER",
                    and_(
                        StudentApplication.payment_method == "ONLINE",
                        StudentApplication.payment_id.is_not(None)
                    )
                )
                statement = statement.where(paid_condition)
                count_query = count_query.where(paid_condition)
            else:
                # "Unpaid": Seulement ONLINE ET payment_id IS NULL (exclure TRANSFER)
                unpaid_condition = and_(
                    StudentApplication.payment_method == "ONLINE",
                    StudentApplication.payment_id.is_(None)
                )
                statement = statement.where(unpaid_condition)
                count_query = count_query.where(unpaid_condition)

        if filters.search is not None:
            like_clause = or_(
                User.first_name.contains(filters.search),
                User.last_name.contains(filters.search),
                User.email.contains(filters.search),
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

        total_count = (await self.session.execute(count_query)).scalar_one()

        # Prioritize TRANSFER (payment_method == "TRANSFER" first)
        priority = case(
            (StudentApplication.payment_method == "TRANSFER", 0),
            else_=1
        )

        if filters.order_by == "created_at":
            statement = statement.order_by(priority, StudentApplication.created_at if filters.asc == "asc" else StudentApplication.created_at.desc())
        elif filters.order_by == "application_number":
            statement = statement.order_by(priority, StudentApplication.application_number if filters.asc == "asc" else StudentApplication.application_number.desc())
        elif filters.order_by == "status":
            statement = statement.order_by(priority, StudentApplication.status if filters.asc == "asc" else StudentApplication.status.desc())

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        applications = result.scalars().all()

        # Convert to Pydantic models pour éviter les erreurs de validation
        from src.api.training.schemas import StudentAttachmentOut
        out_applications = []
        for app in applications:
            # Convertir les attachements
            attachments = None
            if app.attachments:
                attachments = [
                    StudentAttachmentOut(
                        id=att.id,
                        application_id=att.application_id,
                        document_type=att.document_type,
                        file_path=att.file_path,
                        created_at=att.created_at,
                        updated_at=att.updated_at
                    )
                    for att in app.attachments
                ]
            
            out_app = StudentApplicationOut(
                id=app.id,
                user_id=app.user_id,
                training_id=app.training_id,
                target_session_id=app.target_session_id,
                application_number=app.application_number,
                status=app.status,
                payment_id=app.payment_id,
                payment_method=app.payment_method or "ONLINE",  # Fallback str
                refusal_reason=app.refusal_reason,
                registration_fee=app.registration_fee,
                training_fee=app.training_fee,
                currency=app.currency,
                training_title=app.training.title if app.training else "N/A",  # Maintenant préchargé
                training_session_start_date=app.training_session.start_date if app.training_session else None,
                training_session_end_date=app.training_session.end_date if app.training_session else None,
                user_email=app.user.email if app.user else "N/A",  # Préchargé
                user_first_name=app.user.first_name if app.user else "N/A",
                user_last_name=app.user.last_name if app.user else "N/A",
                attachments=attachments,
                created_at=app.created_at,
                updated_at=app.updated_at
            )
            out_applications.append(out_app)

        return out_applications, total_count
    
    async def delete_student_application(self, application: StudentApplication) -> StudentApplication:
        """Delete student application"""
        await self.dissociate_student_attachment(application_id=application.id)
        await self.session.delete(application)
        await self.session.commit()
        return application

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
            description=f"Payment for training fee of session {fullname}",
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
        
    