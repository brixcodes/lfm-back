from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException,status
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, or_
from slugify import slugify
from src.api.payments.models import Payment, PaymentStatusEnum
from src.database import get_session_async
from src.api.job_offers.models import JobOffer, JobApplication, JobAttachment, JobApplicationCode, ApplicationStatusEnum
from src.api.job_offers.schemas import JobApplicationCreateInput, JobApplicationUpdateByCandidateInput, JobAttachmentInput, JobOfferFilter, JobApplicationFilter, UpdateJobOfferStatusInput
from src.api.auth.utils import generate_random_code
from src.config import settings
from src.helper.file_helper import FileHelper
from src.helper.notifications import JobApplicationConfirmationNotification, JobApplicationOTPNotification
from src.helper.schemas import BaseOutFail, ErrorMessage


class JobOfferService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session

    # Job Offers
    async def create_job_offer(self, data) -> JobOffer:
        job_offer = JobOffer(**data.model_dump())
        self.session.add(job_offer)
        await self.session.commit()
        await self.session.refresh(job_offer)
        return job_offer

    async def update_job_offer(self, job_offer: JobOffer, data) -> JobOffer:
        for key, value in data.model_dump(exclude_none=True).items():
            setattr(job_offer, key, value)
        self.session.add(job_offer)
        await self.session.commit()
        await self.session.refresh(job_offer)
        return job_offer

    async def get_job_offer_by_id(self, job_offer_id: str) -> Optional[JobOffer]:
        statement = select(JobOffer).where(JobOffer.id == job_offer_id, JobOffer.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_job_offer_by_reference(self, reference: str) -> Optional[JobOffer]:
        statement = select(JobOffer).where(JobOffer.reference == reference, JobOffer.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_job_offers(self, filters: JobOfferFilter) -> Tuple[List[JobOffer], int]:
        statement = select(JobOffer).where(JobOffer.delete_at.is_(None))
        count_query = select(func.count(JobOffer.id)).where(JobOffer.delete_at.is_(None))

        if filters.search is not None:
            like_clause = or_(
                JobOffer.title.contains(filters.search),
                JobOffer.main_mission.contains(filters.search),
                JobOffer.responsibilities.contains(filters.search),
                JobOffer.competencies.contains(filters.search),
            )
            statement = statement.where(like_clause)
            count_query = count_query.where(like_clause)

        if filters.location is not None:
            statement = statement.where(JobOffer.location.contains(filters.location))
            count_query = count_query.where(JobOffer.location.contains(filters.location))

        if filters.contract_type is not None:
            statement = statement.where(JobOffer.contract_type == filters.contract_type)
            count_query = count_query.where(JobOffer.contract_type == filters.contract_type)

        if filters.salary_min is not None:
            statement = statement.where(JobOffer.salary >= filters.salary_min)
            count_query = count_query.where(JobOffer.salary >= filters.salary_min)

        if filters.salary_max is not None:
            statement = statement.where(JobOffer.salary <= filters.salary_max)
            count_query = count_query.where(JobOffer.salary <= filters.salary_max)

        if filters.order_by == "created_at":
            statement = statement.order_by(JobOffer.created_at if filters.asc == "asc" else JobOffer.created_at.desc())
        elif filters.order_by == "submission_deadline":
            statement = statement.order_by(JobOffer.submission_deadline if filters.asc == "asc" else JobOffer.submission_deadline.desc())
        elif filters.order_by == "title":
            statement = statement.order_by(JobOffer.title if filters.asc == "asc" else JobOffer.title.desc())
        elif filters.order_by == "salary":
            statement = statement.order_by(JobOffer.salary if filters.asc == "asc" else JobOffer.salary.desc())

        total_count = (await self.session.execute(count_query)).scalar_one()

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count

    async def delete_job_offer(self, job_offer: JobOffer) -> JobOffer:
        job_offer.delete_at = datetime.now(timezone.utc)
        self.session.add(job_offer)
        await self.session.commit()
        return job_offer

    # Job Applications
    async def create_job_application(self,job_offer: JobOffer, data : JobApplicationCreateInput) -> JobApplication:
        # Generate application number
        statement = select(func.count(JobApplication.id)).where(JobApplication.job_offer_id == job_offer.id)
        result = await self.session.execute(statement)
        count = result.scalar() or 0
        sequence_number = f"{count + 1:04d}"  # 4-digit, zero-padded
        
        # Generate application number
        application_number = f"APP-{job_offer.reference}-{sequence_number}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        data_attachment = []
        
        for attachment in data.attachments:
            # Créer un nouvel objet JobAttachment avec les données fournies
            doc = JobAttachment(
                file_path=attachment.url,
                document_type=attachment.type,
                name=attachment.name
            )
            self.session.add(doc)
            await self.session.commit()
            await self.session.refresh(doc)
            data_attachment.append(doc)
        
        application_data = data.model_dump()
        del application_data['attachments']
        application_data['application_number'] = application_number
        application_data["currency"] = job_offer.currency
        application_data["submission_fee"] = job_offer.submission_fee
        
        job_application = JobApplication(**application_data)
        self.session.add(job_application)
        await self.session.commit()
        await self.session.refresh(job_application)
        
        for attachment in data_attachment:
            
            await self.associate_job_attachment( attachment=attachment,application_id=job_application.id)
        
        
        return job_application
    
    async def delete_job_application(self, application: JobApplication) -> JobApplication:
        
        await self.dissociate_job_attachment(application_id=application.id)
        
        await self.session.delete(application)
        await self.session.commit()
        return application

    async def get_job_application_by_id(self, application_id: int) -> Optional[JobApplication]:
        statement = select(JobApplication).where(JobApplication.id == application_id, JobApplication.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_job_application_by_number(self, application_number: str) -> Optional[JobApplication]:
        statement = select(JobApplication).where(JobApplication.application_number == application_number, JobApplication.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def get_full_job_application_by_id(self, application_id: int) -> Optional[JobApplication]:
        statement = (
            select(JobApplication)
            .where(JobApplication.id == application_id, JobApplication.delete_at.is_(None))
            .options(selectinload(JobApplication.job_offer))
            .options(selectinload(JobApplication.attachments))
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_job_applications(self, filters: JobApplicationFilter) -> Tuple[List[JobApplication], int]:
        statement = (
            select(JobApplication)
            .join(JobOffer, JobOffer.id == JobApplication.job_offer_id)
            .where(JobApplication.delete_at.is_(None))
        )
        count_query = select(func.count(JobApplication.id)).where(JobApplication.delete_at.is_(None))
        
        if filters.is_paid is not None and filters.is_paid == True:
            statement = statement.where(JobApplication.payment_id == None)
            count_query = count_query.where(JobApplication.status == None)

        if filters.search is not None:
            like_clause = or_(
                JobApplication.first_name.contains(filters.search),
                JobApplication.last_name.contains(filters.search),
                JobApplication.email.contains(filters.search),
                JobOffer.title.contains(filters.search),
                JobOffer.reference.contains(filters.search),
                JobApplication.application_number.contains(filters.search),
            )
            statement = statement.where(like_clause)
            count_query = count_query.where(like_clause)

        if filters.status is not None:
            statement = statement.where(JobApplication.status == filters.status)
            count_query = count_query.where(JobApplication.status == filters.status)

        if filters.job_offer_id is not None:
            statement = statement.where(JobApplication.job_offer_id == filters.job_offer_id)
            count_query = count_query.where(JobApplication.job_offer_id == filters.job_offer_id)

        if filters.order_by == "created_at":
            statement = statement.order_by(JobApplication.created_at if filters.asc == "asc" else JobApplication.created_at.desc())
        elif filters.order_by == "application_number":
            statement = statement.order_by(JobApplication.application_number if filters.asc == "asc" else JobApplication.application_number.desc())
        elif filters.order_by == "status":
            statement = statement.order_by(JobApplication.status if filters.asc == "asc" else JobApplication.status.desc())

        total_count = (await self.session.execute(count_query)).scalar_one()

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count


    # Job Attachments
    async def create_job_attachment(self, data: JobAttachmentInput) -> JobAttachment:
        cover_url, _, _ = await FileHelper.upload_file(
                data.file, f"/job-applications", slugify(data.name)
            )
        attachment = JobAttachment(
            file_path=cover_url,
            document_type=data.name,
            name=data.name
        )
        self.session.add(attachment)
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment


    async def associate_job_attachment(self, attachment: JobAttachment, application_id: int) -> JobAttachment:
        attachment.application_id = application_id
        self.session.add(attachment)
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment
    
    async def dissociate_job_attachment(self, application_id: int) -> None:
        statement = update(JobAttachment).where(JobAttachment.application_id == application_id).values(application_id=None)
        await self.session.execute(statement)
        await self.session.commit()

    async def get_job_attachment_by_id(self, attachment_id: int) -> Optional[JobAttachment]:
        statement = select(JobAttachment).where(JobAttachment.id == attachment_id, JobAttachment.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def get_job_attachment_by_url(self, url: str) -> Optional[JobAttachment]:
        statement = select(JobAttachment).where(JobAttachment.file_path == url, JobAttachment.delete_at.is_(None))
        result = await self.session.execute(statement)
        return result.scalars().first()
    
    async def get_job_attachment_by_type_and_application_id(self, document_type :str, application_id: int) -> Optional[JobAttachment]:
        statement = select(JobAttachment).where(JobAttachment.document_type == document_type, JobAttachment.application_id == application_id)
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def list_attachments_by_application(self, application_id: int) -> List[JobAttachment]:
        statement = (
            select(JobAttachment)
            .where(JobAttachment.application_id == application_id, JobAttachment.delete_at.is_(None))
            .order_by(JobAttachment.created_at)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_job_attachment_by_application_and_type(self, application_id: int, document_type: str) -> JobAttachment:
        attachment = await self.get_job_attachment_by_type_and_application_id(document_type, application_id)
        if attachment is None:
            return None
        FileHelper.delete_file(attachment.file_path)
        self.session.delete(attachment)
        await self.session.commit()
        return attachment
    
    async def delete_job_attachment(self, attachment: JobAttachment) -> JobAttachment:
    
        FileHelper.delete_file(attachment.file_path)
        self.session.delete(attachment)
        await self.session.commit()
        return attachment

    # OTP Methods for Job Applications
    async def generate_application_otp(self, application_number: str, email: str) -> str:
        # Find application by number and email
        statement = select(JobApplication).where(
            JobApplication.application_number == application_number,
            JobApplication.email == email,
            JobApplication.delete_at.is_(None)
        )
        result = await self.session.execute(statement)
        application = result.scalars().first()
        
        if application is None:
            return None
            
        # Generate OTP code
        code = generate_random_code()
        
        # Save OTP code
        otp_code = JobApplicationCode(
            application_id=application.id,
            email=email,
            code=code,
            end_time=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_CODE_EXPIRE_MINUTES)
        )
        
        self.session.add(otp_code)
        await self.session.commit()
        
        # Send OTP email
        await self._send_application_otp_email(application, code)
        
        return code

    async def verify_application_otp(self, application_number: str, email: str, code: str) -> Optional[JobApplication]:
        # Find application
        statement = select(JobApplication).where(
            JobApplication.application_number == application_number,
            JobApplication.email == email,
            JobApplication.delete_at.is_(None)
        )
        result = await self.session.execute(statement)
        application = result.scalars().first()
        
        if application is None:
            return None
            
        # Verify OTP code
        otp_statement = select(JobApplicationCode).where(
            JobApplicationCode.application_id == application.id,
            JobApplicationCode.email == email,
            JobApplicationCode.code == code,
            JobApplicationCode.active == True,
            JobApplicationCode.end_time > datetime.now(timezone.utc)
        )
        otp_result = await self.session.execute(otp_statement)
        otp_code = otp_result.scalars().first()
        
        if otp_code is None:
            return None
            
        # Deactivate the OTP code after use
        otp_code.active = False
        self.session.add(otp_code)
        await self.session.commit()
        
        return application

    async def update_application_by_candidate(self, application: JobApplication, data :JobApplicationUpdateByCandidateInput) -> JobApplication:
        # Update only allowed fields for candidates
        allowed_fields = ['phone_number', 'first_name', 'last_name', 'civility', 'country_code', 'date_of_birth',"attachments"]
        attachment_data = []
        for attachment in data.attachments:
            
            doc = await self.get_job_attachment_by_url(attachment.url)
            if doc is None or (doc.application_id is not None and doc.application_id != application.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=BaseOutFail(
                        message=ErrorMessage.JOB_ATTACHMENT_NOT_FOUND.description + f" ({attachment})",
                        error_code=ErrorMessage.JOB_ATTACHMENT_NOT_FOUND.value,
                    ).model_dump(),
                )
            elif doc.application_id is None :
                attachment_data.append(doc)
                
    
        for key, value in data.model_dump(exclude_none=True).items():
            if key in allowed_fields:
                setattr(application, key, value)

        self.session.add(application)
        await self.session.commit()
        await self.session.refresh(application)
        
        # Update job application attachments
        for attachment in attachment_data:
            await self.delete_job_attachment_by_application_and_type(application.id, attachment.document_type)
            await self.associate_job_attachment(attachment, application.id)
        return application

    async def change_job_application_status(self,application: JobApplication, input: UpdateJobOfferStatusInput) -> List[JobApplication]:
    
        application.status = input.status
        application.refusal_reason = input.reason
        self.session.add(application)
        await self.session.commit()
        await self.session.refresh(application)
        
        return application
    
    async def update_job_application_payment(self,application_id: int,payment_id:str) :
    
        application = await self.get_job_application_by_id(application_id)
        application.payment_id = payment_id
        self.session.add(application)
        await self.session.commit()
        
        return application
    
    # Private email methods
    async def send_application_confirmation_email(self, application: JobApplication):
        """Send confirmation email when job application is created"""
        # Get job offer details
        job_offer = await self.get_job_offer_by_id(application.job_offer_id)
        if job_offer is None:
            return
            
        notification = JobApplicationConfirmationNotification(
            email=application.email,
            application_number=application.application_number,
            job_title=job_offer.title,
            candidate_name=f"{application.first_name} {application.last_name}",
            lang="en"  # Default to English, could be made configurable
        )
        
        notification.send_notification()

    async def _send_application_otp_email(self, application: JobApplication, code: str):
        """Send OTP email for application updates"""
        notification = JobApplicationOTPNotification(
            email=application.email,
            code=code,
            application_number=application.application_number,
            candidate_name=f"{application.first_name} {application.last_name}",
            lang="en"  # Default to English, could be made configurable
        )
        
        notification.send_notification()
