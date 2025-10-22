from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import string
from fastapi import Depends, HTTPException, status

from src.database import get_session_async
from src.api.user.models import User, UserStatusEnum, UserTypeEnum
from src.api.user.schemas import CreateUserInput
from src.api.user.service import UserService
from src.api.payments.service import PaymentService
from src.helper.notifications import NotificationService
from fastapi import Request
from .models import CabinetApplication, ApplicationFee, CabinetApplicationStatus, PaymentStatus
from .schemas import (
    CabinetApplicationCreate, CabinetApplicationUpdate, CabinetApplicationOut,
    ApplicationFeeCreate, ApplicationFeeUpdate, ApplicationFeeOut,
    CabinetApplicationPaymentResponse, PaymentWebhookData, CabinetApplicationCredentials,
    CabinetApplicationStats
)
from src.api.auth.service import AuthService

class CabinetApplicationService:
    def __init__(self, session: AsyncSession = Depends(get_session_async)):
        self.session = session
        self.payment_service = PaymentService(session)
        self.notification_service = NotificationService()
        self.user_service = UserService(session)

    async def create_application(self, application_data: CabinetApplicationCreate, request: Request = None) -> CabinetApplicationOut:
        try:
            print("Checking for existing application...")
            existing_application = await self.session.execute(
                select(CabinetApplication).where(
                    CabinetApplication.contact_email == application_data.contact_email
                )
            )
            if existing_application.scalar_one_or_none():
                raise ValueError("Une candidature existe déjà pour cet email")

            print("Creating new application...")
            application = CabinetApplication(
                **application_data.dict(),
                status=CabinetApplicationStatus.PENDING,
                payment_status=PaymentStatus.PENDING,
                payment_amount=50.0,
                payment_currency="EUR",
                campaign_id=None  # Set to a specific campaign_id if required
            )
            
            print("Adding application to session...")
            self.session.add(application)
            print("Committing session...")
            await self.session.commit()
            print("Refreshing application...")
            await self.session.refresh(application)
            
            print("Initiating payment...")
            payment_result = await self._submit_cabinet_application(application)
            
            print("Creating response...")
            # Debug: log payment result
            print(f"Payment result: {payment_result}")
            print(f"Payment link: {payment_result.get('payment_link')}")
            print(f"Transaction ID: {payment_result.get('transaction_id')}")
            
            # Créer manuellement l'objet de réponse avec payment_url
            application_out = CabinetApplicationOut(
                id=str(application.id),
                company_name=application.company_name,
                contact_email=application.contact_email,
                contact_phone=application.contact_phone,
                address=application.address,
                registration_number=application.registration_number,
                experience_years=application.experience_years,
                qualifications=application.qualifications,
                technical_proposal=application.technical_proposal,
                financial_proposal=application.financial_proposal,
                references=application.references,
                status=application.status,
                payment_status=application.payment_status,
                payment_reference=payment_result.get("transaction_id"),
                payment_amount=application.payment_amount,
                payment_currency=application.payment_currency,
                payment_date=application.payment_date,
                account_created=application.account_created,
                credentials_sent=application.credentials_sent,
                created_at=application.created_at,
                updated_at=application.updated_at,
                payment_url=payment_result.get("payment_link")
            )
            
            return application_out
            
        except Exception as e:
            await self.session.rollback()
            print(f"Error in create_application: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur interne: {str(e)}")
                

    async def get_application_by_id(self, application_id: str) -> Optional[CabinetApplicationOut]:
        """Récupérer une candidature par son ID"""
        result = await self.session.execute(
            select(CabinetApplication).where(CabinetApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if application:
            return CabinetApplicationOut.model_validate(application.model_dump())
        return None

    async def get_application_by_email(self, email: str) -> Optional[CabinetApplicationOut]:
        """Récupérer une candidature par email"""
        result = await self.session.execute(
            select(CabinetApplication).where(CabinetApplication.contact_email == email)
        )
        application = result.scalar_one_or_none()
        
        if application:
            return CabinetApplicationOut.model_validate(application.model_dump())
        return None

    async def get_payment_status(self, application_id: str) -> dict:
        """Récupérer le statut de paiement d'une candidature"""
        application = await self.session.get(CabinetApplication, application_id)
        if not application:
            raise ValueError("Candidature non trouvée")
        
        return {
            "application_id": application_id,
            "payment_status": application.payment_status,
            "payment_reference": application.payment_reference,
            "payment_amount": application.payment_amount,
            "payment_currency": application.payment_currency,
            "payment_date": application.payment_date,
            "status": application.status
        }

    async def update_application(self, application_id: str, update_data: CabinetApplicationUpdate) -> Optional[CabinetApplicationOut]:
        """Mettre à jour une candidature - SEUL LE PAIEMENT PEUT CHANGER LE STATUT"""
        result = await self.session.execute(
            select(CabinetApplication).where(CabinetApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return None
        
        # Empêcher la modification du statut et du statut de paiement
        update_dict = update_data.dict(exclude_unset=True)
        
        # Champs interdits à la modification manuelle
        forbidden_fields = ['status', 'payment_status', 'payment_reference', 'payment_date', 'user_id', 'account_created', 'credentials_sent']
        
        for field in forbidden_fields:
            if field in update_dict:
                del update_dict[field]
                print(f"Champ '{field}' ignoré - seul le paiement peut le modifier")
        
        # Mettre à jour uniquement les champs autorisés
        for field, value in update_dict.items():
            setattr(application, field, value)
        
        application.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(application)
        
        return CabinetApplicationOut.model_validate(application.model_dump())

    async def _submit_cabinet_application(self, application: CabinetApplication) -> dict:
        try:
            print("Preparing payment input...")
            from src.api.payments.schemas import PaymentInitInput
            payment_input = PaymentInitInput(
                payable=application,
                amount=application.payment_amount,
                product_currency=application.payment_currency,
                description=f"Frais de candidature cabinet LAFAOM - {application.company_name}",
                payment_provider="CINETPAY",
                customer_name=application.company_name,
                customer_surname="Cabinet",
                customer_email=application.contact_email,
                customer_phone_number=application.contact_phone,
                customer_address=application.address,
                customer_city="Dakar",  # Ville par défaut pour le Sénégal
                customer_country="SN",  # Code pays Sénégal
                customer_state="SN",
                customer_zip_code="00000"
            )
            print("Initiating payment with PaymentService...")
            payment_result = await self.payment_service.initiate_payment(payment_input)
            if not payment_result.get("success"):
                raise ValueError(f"Payment initiation failed: {payment_result.get('message')}")
            print("Payment initiated successfully:", payment_result)
            return payment_result
        except Exception as e:
            print(f"Payment error: {str(e)}")
            raise ValueError(f"Erreur lors de l'initiation du paiement: {str(e)}")
                
    async def initiate_payment(self, application_id: str) -> CabinetApplicationPaymentResponse:
        """Initier le paiement pour une candidature"""
        application = await self.session.get(CabinetApplication, application_id)
        if not application:
            raise ValueError("Candidature non trouvée")
        
        if application.payment_status == PaymentStatus.PAID:
            raise ValueError("Le paiement a déjà été effectué")
        
        # Générer une référence de paiement unique
        payment_reference = f"CAB_{application_id.hex[:8].upper()}_{int(datetime.utcnow().timestamp())}"
        
        # Préparer les données de paiement
        payment_data = {
            "amount": application.payment_amount,
            "currency": application.payment_currency,
            "description": f"Frais de candidature cabinet LAFAOM - {application.company_name}",
            "customer_email": application.contact_email,
            "customer_name": application.company_name,
            "return_url": f"https://lafaom.vertex-cam.com/cabinet-application/success/{application_id}",
            "cancel_url": f"https://lafaom.vertex-cam.com/cabinet-application/cancel/{application_id}",
            "webhook_url": "https://lafaom.vertex-cam.com/api/v1/cabinet-application/payment-webhook"
        }
        
        # Initier le paiement avec CinetPay
        payment_result = await self.payment_service.initiate_payment(payment_data)
        
        if not payment_result.get("success"):
            raise ValueError(f"Erreur lors de l'initiation du paiement: {payment_result.get('message')}")
        
        # Mettre à jour la candidature avec la référence de paiement
        application.payment_reference = payment_reference
        await self.session.commit()
        
        return CabinetApplicationPaymentResponse(
            application_id=application_id,
            payment_url=payment_result["payment_url"],
            payment_reference=payment_reference,
            amount=application.payment_amount,
            currency=application.payment_currency,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )

    async def handle_payment_webhook(self, webhook_data: PaymentWebhookData, request: Request = None) -> bool:
        """Traiter le webhook de paiement - SEUL le paiement peut changer le statut à PAID"""
        try:
            # Trouver la candidature par référence de paiement
            application = await self.session.execute(
                select(CabinetApplication).where(
                    CabinetApplication.payment_reference == webhook_data.payment_reference
                )
            )
            application = application.scalar_one_or_none()
            
            if not application:
                print(f"Candidature non trouvée pour la référence: {webhook_data.payment_reference}")
                return False
            
            # Vérifier que la candidature est en attente de paiement
            if application.payment_status != PaymentStatus.PENDING:
                print(f"Candidature {application.id} n'est pas en attente de paiement (statut: {application.payment_status})")
                return False
            
            if webhook_data.status == "success":
                # SEUL LE PAIEMENT PEUT CHANGER LE STATUT À PAID
                application.payment_status = PaymentStatus.PAID
                application.payment_date = datetime.utcnow()
                application.status = CabinetApplicationStatus.PAID
                
                # Créer le compte utilisateur automatiquement
                await self._create_cabinet_user(application, request)
                
                await self.session.commit()
                print(f"Paiement confirmé pour la candidature {application.id}")
                return True
                
            elif webhook_data.status == "failed":
                application.payment_status = PaymentStatus.FAILED
                # Le statut reste PENDING en cas d'échec
                await self.session.commit()
                print(f"Paiement échoué pour la candidature {application.id}")
                return True
                
        except Exception as e:
            print(f"Erreur lors du traitement du webhook: {e}")
            return False
        
        return False

    async def _create_cabinet_user(self, application: CabinetApplication, request: Request = None) -> None:
        """Créer un compte utilisateur pour le cabinet"""
        try:
            # Générer un nom d'utilisateur unique
            username = f"cabinet_{application.company_name.lower().replace(' ', '_')}_{application.id.hex[:8]}"
            
            # Générer un mot de passe temporaire
            temp_password = self._generate_temp_password()
            
            # Créer l'utilisateur
            user_data = CreateUserInput(
                first_name=application.company_name,
                last_name="Cabinet",
                password=temp_password,
                email=application.contact_email,
                mobile_number=application.contact_phone,
                status=UserStatusEnum.ACTIVE,
                user_type=UserTypeEnum.STAFF,
                two_factor_enabled=False,
                web_token=None
            )
            
            user = await self.user_service.create_user(user_data)
            
            # Mettre à jour la candidature
            application.user_id = user.id
            application.account_created = True
            
            # Envoyer les identifiants par email
            await self._send_credentials_email(application, username, temp_password, request)
            
        except Exception as e:
            print(f"Erreur lors de la création du compte utilisateur: {e}")
            raise e

    def _generate_temp_password(self, length: int = 12) -> str:
        """Générer un mot de passe temporaire"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))

    async def _send_credentials_email(self, application: CabinetApplication, username: str, password: str, request: Request = None) -> None:
        """Envoyer les identifiants par email"""
        try:
            # Récupérer l'URL de base automatiquement
            if request:
                base_url = str(request.base_url).rstrip('/')
            else:
                # Fallback si pas de request disponible
                base_url = "https://lafaom.vertex-cam.com"
            
            credentials = CabinetApplicationCredentials(
                email=application.contact_email,
                username=username,
                temporary_password=password,
                login_url=f"{base_url}/auth/login"
            )
            
            # Envoyer l'email avec les identifiants
            await self.notification_service.send_cabinet_credentials_email(credentials)
            
            application.credentials_sent = True
            
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {e}")
            raise e

    async def get_applications_stats(self) -> CabinetApplicationStats:
        """Récupérer les statistiques des candidatures"""
        # Compter les candidatures par statut
        total_result = await self.session.execute(
            select(func.count(CabinetApplication.id))
        )
        total_applications = total_result.scalar()
        
        pending_result = await self.session.execute(
            select(func.count(CabinetApplication.id)).where(
                CabinetApplication.status == CabinetApplicationStatus.PENDING
            )
        )
        pending_applications = pending_result.scalar()
        
        paid_result = await self.session.execute(
            select(func.count(CabinetApplication.id)).where(
                CabinetApplication.payment_status == PaymentStatus.PAID
            )
        )
        paid_applications = paid_result.scalar()
        
        approved_result = await self.session.execute(
            select(func.count(CabinetApplication.id)).where(
                CabinetApplication.status == CabinetApplicationStatus.APPROVED
            )
        )
        approved_applications = approved_result.scalar()
        
        rejected_result = await self.session.execute(
            select(func.count(CabinetApplication.id)).where(
                CabinetApplication.status == CabinetApplicationStatus.REJECTED
            )
        )
        rejected_applications = rejected_result.scalar()
        
        # Calculer le revenu total
        revenue_result = await self.session.execute(
            select(func.sum(CabinetApplication.payment_amount)).where(
                CabinetApplication.payment_status == PaymentStatus.PAID
            )
        )
        total_revenue = revenue_result.scalar() or 0.0
        
        return CabinetApplicationStats(
            total_applications=total_applications,
            pending_applications=pending_applications,
            paid_applications=paid_applications,
            approved_applications=approved_applications,
            rejected_applications=rejected_applications,
            total_revenue=total_revenue,
            currency="EUR"
        )

    async def list_applications(self, skip: int = 0, limit: int = 100, status: Optional[CabinetApplicationStatus] = None) -> List[CabinetApplicationOut]:
        """Lister les candidatures avec filtres"""
        query = select(CabinetApplication)
        
        if status:
            query = query.where(CabinetApplication.status == status)
        
        query = query.offset(skip).limit(limit).order_by(CabinetApplication.created_at.desc())
        
        result = await self.session.execute(query)
        applications = result.scalars().all()
        
        return [CabinetApplicationOut.model_validate(app.model_dump()) for app in applications]

    async def get_paid_applications(self, skip: int = 0, limit: int = 100) -> List[CabinetApplicationOut]:
        """Récupérer les candidatures qui ont payé les frais"""
        query = select(CabinetApplication).where(
            CabinetApplication.payment_status == PaymentStatus.PAID
        )
        
        query = query.offset(skip).limit(limit).order_by(CabinetApplication.payment_date.desc())
        
        result = await self.session.execute(query)
        applications = result.scalars().all()
        
        return [CabinetApplicationOut.model_validate(app.model_dump()) for app in applications]

    async def get_my_applications(self, user_email: str, skip: int = 0, limit: int = 100) -> List[CabinetApplicationOut]:
        """Récupérer les candidatures de l'utilisateur connecté"""
        query = select(CabinetApplication).where(
            CabinetApplication.contact_email == user_email
        )
        
        query = query.offset(skip).limit(limit).order_by(CabinetApplication.created_at.desc())
        
        result = await self.session.execute(query)
        applications = result.scalars().all()
        
        return [CabinetApplicationOut.model_validate(app.model_dump()) for app in applications]

    async def approve_application(self, application_id: str) -> CabinetApplicationOut:
        """Approuver une candidature de cabinet"""
        # Récupérer la candidature
        result = await self.session.execute(
            select(CabinetApplication).where(CabinetApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            raise ValueError("Candidature non trouvée")
        
        if application.status != CabinetApplicationStatus.PENDING:
            raise ValueError("Seules les candidatures en attente peuvent être approuvées")
        
        # Mettre à jour le statut
        application.status = CabinetApplicationStatus.APPROVED
        
        # Créer un compte utilisateur pour le cabinet
        try:
            user_data = {
                "email": application.contact_email,
                "first_name": application.company_name,
                "last_name": "",
                "phone_number": application.contact_phone,
                "is_active": True,
                "is_verified": True
            }
            
            # Générer un mot de passe temporaire
            import secrets
            import string
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            # Créer l'utilisateur
            user = await self.user_service.create_user_with_password(user_data, password)
            application.user_id = user.id
            application.account_created = True
            
            # Envoyer les identifiants par email
            await self._send_credentials_email(application, user.email, password)
            application.credentials_sent = True
            
        except Exception as e:
            print(f"Erreur lors de la création du compte utilisateur: {e}")
            # Continuer même si la création du compte échoue
        
        await self.session.commit()
        await self.session.refresh(application)
        
        return CabinetApplicationOut.model_validate(application.model_dump())

    async def reject_application(self, application_id: str, reason: Optional[str] = None) -> CabinetApplicationOut:
        """Rejeter une candidature de cabinet"""
        # Récupérer la candidature
        result = await self.session.execute(
            select(CabinetApplication).where(CabinetApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            raise ValueError("Candidature non trouvée")
        
        if application.status != CabinetApplicationStatus.PENDING:
            raise ValueError("Seules les candidatures en attente peuvent être rejetées")
        
        # Mettre à jour le statut
        application.status = CabinetApplicationStatus.REJECTED
        
        # Optionnel: ajouter la raison du rejet dans les qualifications
        if reason:
            application.qualifications = f"Rejetée: {reason}"
        
        await self.session.commit()
        await self.session.refresh(application)
        
        return CabinetApplicationOut.model_validate(application.model_dump())

class ApplicationFeeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_fee(self, fee_data: ApplicationFeeCreate) -> ApplicationFeeOut:
        """Créer de nouveaux frais de candidature"""
        fee = ApplicationFee(**fee_data.dict())
        self.session.add(fee)
        await self.session.commit()
        await self.session.refresh(fee)
        return ApplicationFeeOut.model_validate(fee)

    async def get_fee_by_id(self, fee_id: str) -> Optional[ApplicationFeeOut]:
        """Récupérer des frais par ID"""
        result = await self.session.execute(
            select(ApplicationFee).where(ApplicationFee.id == fee_id)
        )
        fee = result.scalar_one_or_none()
        
        if fee:
            return ApplicationFeeOut.model_validate(fee)
        return None

    async def update_fee(self, fee_id: str, update_data: ApplicationFeeUpdate) -> Optional[ApplicationFeeOut]:
        """Mettre à jour des frais"""
        result = await self.session.execute(
            select(ApplicationFee).where(ApplicationFee.id == fee_id)
        )
        fee = result.scalar_one_or_none()
        
        if not fee:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(fee, field, value)
        
        fee.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(fee)
        
        return ApplicationFeeOut.model_validate(fee)

    async def list_fees(self, skip: int = 0, limit: int = 100) -> List[ApplicationFeeOut]:
        """Lister les frais de candidature"""
        result = await self.session.execute(
            select(ApplicationFee)
            .offset(skip)
            .limit(limit)
            .order_by(ApplicationFee.created_at.desc())
        )
        fees = result.scalars().all()
        
        return [ApplicationFeeOut.model_validate(fee) for fee in fees]
