
import asyncio
import json
import math
import re
from celery import shared_task
from fastapi import Depends
import httpx
from sqlalchemy import func, or_
from sqlmodel import select ,Session
from src.api.job_offers.models import JobApplication
from src.api.job_offers.service import JobOfferService
from src.api.training.models import StudentApplication, TrainingFeeInstallmentPayment
from src.config import settings
from src.api.payments.models import CinetPayPayment, Payment, PaymentStatusEnum
from src.api.payments.schemas import CinetPayInit, PaymentFilter, PaymentInitInput
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session, get_session_async
from src.api.user.models import User, UserStatusEnum, UserTypeEnum
from src.api.user.schemas import CreateUserInput
from src.api.user.service import UserService
from src.helper.notifications import NotificationService
from src.helper.utils import clean_payment_description, clean_cinetpay_string
import secrets
import string
from src.redis_client import get_from_redis, set_to_redis


class PaymentService:
    
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session
        
    @staticmethod
    def round_up_to_nearest_5(x: float) -> int:
        return int(math.ceil(x / 5.0)) * 5
    
    async def list_payments(self, filters: PaymentFilter):
        
        statement = (
            select(Payment)
            .where(Payment.delete_at.is_(None))
        )
        count_query = select(func.count(Payment.id)).where(Payment.delete_at.is_(None))
        
        print(filters)

        if filters.search is not None:
            like_clause = or_(
                Payment.transaction_id.contains(filters.search),
                Payment.payable_type.contains(filters.search),
                Payment.payment_type.contains(filters.search),
                Payment.product_currency.contains(filters.search),
            )
            statement = statement.where(like_clause)
            count_query = count_query.where(like_clause)
            
        if filters.currency is not None:
            statement = statement.where(Payment.product_currency == filters.currency)
            count_query = count_query.where(Payment.product_currency == filters.currency)

        if filters.status is not None:
            statement = statement.where(Payment.status == filters.status)
            count_query = count_query.where(Payment.status == filters.status)

        if filters.min_amount is not None:
            statement = statement.where(Payment.product_amount >= filters.min_amount)
            count_query = count_query.where(Payment.product_amount >= filters.min_amount)
            
        if filters.max_amount is not None:
            statement = statement.where(Payment.product_amount <= filters.max_amount)
            count_query = count_query.where(Payment.product_amount <= filters.max_amount)
            
        if filters.date_from is not None:
            statement = statement.where(Payment.created_at >= filters.date_from)
            count_query = count_query.where(Payment.created_at >= filters.date_from)
            
        if filters.date_to is not None:
            statement = statement.where(Payment.created_at <= filters.date_to)
            count_query = count_query.where(Payment.created_at <= filters.date_to)

        if filters.order_by == "created_at":
            statement = statement.order_by(Payment.created_at if filters.asc == "asc" else Payment.created_at.desc())
        elif filters.order_by == "amount":
            statement = statement.order_by(Payment.product_amount if filters.asc == "asc" else Payment.product_amount.desc())
        elif filters.order_by == "status":
            statement = statement.order_by(Payment.status if filters.asc == "asc" else Payment.status.desc())

        total_count = (await self.session.execute(count_query)).scalar_one()

        statement = statement.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
        result = await self.session.execute(statement)
        return result.scalars().all(), total_count
    
    async def get_payment_by_payable(self, payable_id: str, payable_type: str):
        statement = select(Payment).where(Payment.payable_id == payable_id).where(Payment.payable_type == payable_type)
        result = await self.session.execute(statement)
        payment = result.scalars().first()
        return payment
    
    async def get_payment_by_transaction_id(self, transaction_id: str):
        statement = select(Payment).where(Payment.transaction_id == transaction_id)
        result = await self.session.execute(statement)
        payment = result.scalars().first()
        return payment
        
    async def get_payment_by_payment_type(self, payment_type: str, payment_type_id: str):
        statement = select(Payment).where(Payment.payment_type == payment_type).where(Payment.payment_type_id == payment_type_id)
        result = await self.session.execute(statement)
        payment = result.scalars().first()
        return payment
    
    async def get_currency_rates(self, from_currency: str, to_currencies: list[str] = None):
        
        cache_key = f"currency:{from_currency}:{','.join(to_currencies) if to_currencies else 'ALL'}"

        # Check cache
        try:
            cached = await get_from_redis(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"Redis cache error: {e}")

        # Si pas d'API key configurée, utiliser des taux par défaut
        if not settings.CURRENCY_API_KEY or settings.CURRENCY_API_KEY == "your_currency_api_key_here":
            print("No currency API key configured, using default rates")
            default_rates = {
                "USDXAF": 600.0,
                "EURXAF": 675.0,
                "XAFUSD": 0.0017,
                "XAFEUR": 0.0015,
            }
            rate_key = f"{from_currency}{to_currencies[0] if to_currencies else 'XAF'}"
            return {rate_key: default_rates.get(rate_key, 1.0)}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "apikey": settings.CURRENCY_API_KEY
                }
                symbols = ",".join(to_currencies) if to_currencies else None
                params = {"source": from_currency}
                if symbols:
                    params["currencies"] = symbols
                
                print(f"Currency API Request - URL: {settings.CURRENCY_API_URL}")
                print(f"Currency API Request - Params: {params}")
                
                response = await client.get(f"{settings.CURRENCY_API_URL}", headers=headers, params=params)
                
                if response.status_code != 200:
                    print(f"Currency API Error: {response.status_code} - {response.text}")
                    raise Exception(f"Currency API returned {response.status_code}")
                
                data = response.json()
                print(f"Currency API Response: {data}")
                
                if 'quotes' not in data:
                    print(f"Currency API Error: No 'quotes' in response: {data}")
                    raise Exception("Invalid currency API response format")
                
                rates = data['quotes']
                
                # Cache the rates
                try:
                    await set_to_redis(cache_key, json.dumps(rates), ex=14400)
                except Exception as e:
                    print(f"Redis cache set error: {e}")
                
                return rates
                
        except Exception as e:
            print(f"Currency API Error: {e}")
            # Fallback to default rates
            default_rates = {
                "USDXAF": 600.0,
                "EURXAF": 650.0,
                "XAFUSD": 0.0017,
                "XAFEUR": 0.0015,
            }
            rate_key = f"{from_currency}{to_currencies[0] if to_currencies else 'XAF'}"
            return {rate_key: default_rates.get(rate_key, 1.0)}

    async def initiate_payment(self, payment_data: PaymentInitInput,is_swallow: bool = False):
        
        if payment_data.payment_provider == "CINETPAY":
            payment_currency = "XAF"  # XAF pour le compte CinetPay
        else :
            payment_currency = payment_data.product_currency

        try:
            quota = await self.get_currency_rates(payment_data.product_currency, [payment_currency])
            product_currency_to_payment_currency_rate = quota[f"{payment_data.product_currency}{payment_currency}"]
        except Exception as e:
            print(f"Currency conversion error: {e}")
            # Utiliser un taux par défaut si la conversion échoue
            if payment_currency == "XAF" and payment_data.product_currency == "EUR":
                product_currency_to_payment_currency_rate = 650.0  # 1 EUR = 650 XAF
            elif payment_currency == "XAF" and payment_data.product_currency == "USD":
                product_currency_to_payment_currency_rate = 600.0  # 1 USD = 600 XAF
            else:
                product_currency_to_payment_currency_rate = 1.0  # Pas de conversion
        
        print(f"Currency Conversion - Original Amount: {payment_data.amount} {payment_data.product_currency}")
        print(f"Currency Conversion - Rate: {product_currency_to_payment_currency_rate}")
        print(f"Currency Conversion - Converted Amount: {payment_data.amount * product_currency_to_payment_currency_rate} {payment_currency}")
        
        try:
            quota = await self.get_currency_rates("USD", [payment_currency, payment_data.product_currency])
            usd_to_payment_currency_rate = quota[f"USD{payment_currency}"]
            usd_to_product_currency_rate = quota[f"USD{payment_data.product_currency}"]
        except Exception as e:
            print(f"USD currency conversion error: {e}")
            # Utiliser des taux par défaut
            usd_to_payment_currency_rate = 600.0 if payment_currency == "XAF" else 1.0
            usd_to_product_currency_rate = 1.0 if payment_data.product_currency == "USD" else 0.0017
        

        # Générer un transaction_id sans caractères spéciaux pour CinetPay
        # CinetPay n'accepte pas certains caractères spéciaux dans transaction_id
        # Limiter à 25 caractères maximum selon la documentation CinetPay
        transaction_id = str(uuid.uuid4()).replace('-', '')[:25]  # Retirer les tirets et limiter à 25 caractères
        
        payment = Payment(
            transaction_id=transaction_id,
            product_amount=payment_data.amount,
            product_currency=payment_data.product_currency,
            payment_currency=payment_currency,
            daily_rate=product_currency_to_payment_currency_rate,
            usd_product_currency_rate=usd_to_product_currency_rate,
            usd_payment_currency_rate=usd_to_payment_currency_rate,
            status=PaymentStatusEnum.PENDING.value,
            payable_id= str(payment_data.payable.id),
            payable_type=payment_data.payable.__class__.__name__
        )
        
        final_amount = PaymentService.round_up_to_nearest_5(payment_data.amount * product_currency_to_payment_currency_rate)
        print(f"CinetPay Amount - Final Amount: {final_amount} {payment_currency}")
        
        # Générer la description selon le type de payable
        # Retirer les caractères spéciaux et utiliser des descriptions spécifiques
        payable_type = payment_data.payable.__class__.__name__
        original_description = (payment_data.description or "").lower()
        
        # Déterminer la description selon le type de payable
        # Vérifier d'abord si c'est une formation (dans la description ou le type)
        if "formation" in original_description or "training" in original_description or "training" in payable_type.lower():
            base_description = "paiement des frais de formation"
        elif payable_type == "StudentApplication":
            # StudentApplication peut être inscription ou formation, vérifier la description
            if "formation" in original_description or "training" in original_description:
                base_description = "paiement des frais de formation"
            else:
                base_description = "paiement des frais inscription"
        elif payable_type == "JobApplication":
            base_description = "paiement des frais offre emploi"
        elif payable_type == "CabinetApplication":
            base_description = "paiement des frais candidature cabinet"
        else:
            # Utiliser la description fournie si aucun mapping n'est trouvé
            base_description = payment_data.description or "paiement"
        
        # Nettoyer la description pour retirer les caractères spéciaux non autorisés par CinetPay
        cleaned_description = clean_payment_description(base_description)
        print(f"Description générée: {cleaned_description} (type: {payable_type})")
        
        # Construire les données CinetPay avec tous les champs requis (identique aux tests qui fonctionnent)
        cinetpay_data = CinetPayInit(
            transaction_id=payment.transaction_id,
            amount=int(final_amount),  # S'assurer que c'est un entier
            currency=payment_currency,
            description=cleaned_description,
            meta=f"{payment_data.payable.__class__.__name__}-{payment_data.payable.id}",
            invoice_data={
                "payable": payment.payable_type,
                "payable_id": payment.payable_id
            },
            customer_name=payment_data.customer_name,
            customer_surname=payment_data.customer_surname,
            customer_email=payment_data.customer_email,
            customer_phone_number=payment_data.customer_phone_number,
            customer_address=payment_data.customer_address,
            customer_city=payment_data.customer_city,
            customer_country=payment_data.customer_country,
            customer_state=payment_data.customer_state,
            customer_zip_code=payment_data.customer_zip_code,
            channels=payment_data.channels,
            lock_phone_number=payment_data.lock_phone_number or False,
            lang=payment_data.lang or "fr"
        )
        
        cinetpay_client = CinetPayService(self.session)
        
        try:
            if is_swallow:
                result = await cinetpay_client.initiate_cinetpay_swallow_payment(cinetpay_data)
            else :
                result = await cinetpay_client.initiate_cinetpay_payment( cinetpay_data)
        except Exception as e:
            return {
                "success": False,
                "message":"unable to initiate payment",
                "amount": payment_data.amount,
                "payment_link": None,
                "transaction_id": None,
                "payment_provider": payment_data.payment_provider,
                "notify_url": settings.CINETPAY_NOTIFY_URL
            }
        
        if result["status"] == "success":
            cinetpay_payment = result["data"]
        else:
            return {
                "success": False,
                "message": result["message"],
                "amount": payment_data.amount,
                "payment_link": None,
                "transaction_id": None,
                "payment_provider": payment_data.payment_provider,
                "notify_url": settings.CINETPAY_NOTIFY_URL
            }
        
        payment.payment_type_id = str(cinetpay_payment.id)
        payment.payment_type = cinetpay_payment.__class__.__name__
        
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        
        return {
            "success": True,
            "payment_provider": payment_data.payment_provider,
            "amount" : payment_data.amount,
            "payment_link": cinetpay_payment.payment_url,
            "transaction_id": cinetpay_payment.transaction_id,
            "notify_url": settings.CINETPAY_NOTIFY_URL,
            "message": ''
        }
        
    async def get_payment_by_id(self, payment_id: str):
        statement = select(Payment).where(Payment.id == payment_id)
        result = await self.session.execute(statement)
        payment = result.scalars().one()
        return payment
    


    async def check_payment_status(self, payment : Payment):
        if payment.payment_type == "CinetPayPayment":
        
            
            cinetpay_client = CinetPayService(self.session)
            cinetpay_payment = await cinetpay_client.get_cinetpay_payment(payment.transaction_id)
            
            if cinetpay_payment is None:
                
                payment.status = PaymentStatusEnum.ERROR
                await self.session.commit()
                await self.session.refresh(payment)
            else :
                result = await  CinetPayService.check_cinetpay_payment_status(payment.transaction_id)
                
                # Gérer les différents statuts selon la documentation CinetPay
                transaction_status = result["data"].get("status", "")
                
                if transaction_status == "ACCEPTED":
                    payment.status = PaymentStatusEnum.ACCEPTED.value
                    cinetpay_payment.status = PaymentStatusEnum.ACCEPTED.value
                    cinetpay_payment.amount_received = float(result["data"].get("amount", 0))
                    cinetpay_payment.payment_method = result["data"].get("payment_method", "")
                    
                    if payment.payable_type == "JobApplication":
                        job_application_service = JobOfferService(session=self.session)
                        job_offer = await job_application_service.update_job_application_payment(payment_id=int(payment.id),application_id=payment.payable_id)
                    
                    elif payment.payable_type == "StudentApplication":
                        statement = select(StudentApplication).where(StudentApplication.id == payment.payable_id)
                        result = await self.session.execute(statement)
                        student_application = result.scalars().one()
                        student_application.payment_id = payment.id
                        await self.session.commit()
                        await self.session.refresh(student_application)
                        print(f"✅ StudentApplication {payment.payable_id} mis à jour avec payment_id: {payment.id}")
                    
                    elif payment.payable_type == "CabinetApplication":
                        from src.api.cabinet.models import CabinetApplication, PaymentStatus
                        from datetime import datetime
                        statement = select(CabinetApplication).where(CabinetApplication.id == payment.payable_id)
                        result = await self.session.execute(statement)
                        cabinet_application = result.scalars().one()
                        cabinet_application.payment_id = payment.id
                        cabinet_application.payment_status = PaymentStatus.PAID
                        cabinet_application.payment_date = datetime.utcnow()
                        await self.session.commit()
                        await self.session.refresh(cabinet_application)
                        print(f"✅ CabinetApplication {payment.payable_id} mis à jour avec payment_id: {payment.id}")
                    
                elif transaction_status in ["REFUSED", "CANCELLED"]:
                    payment.status = PaymentStatusEnum.REFUSED.value
                    cinetpay_payment.status = PaymentStatusEnum.REFUSED.value
                    cinetpay_payment.error_code = result.get("code", "")
                elif transaction_status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", 
                                            "WAITING_CUSTOMER_PAYMENT", "WAITING_CUSTOMER_OTP_CODE"]:
                    # Paiement en attente de confirmation
                    payment.status = PaymentStatusEnum.PENDING.value
                    cinetpay_payment.status = PaymentStatusEnum.PENDING.value
                
                await self.session.commit()
                await self.session.refresh(payment)
                await self.session.refresh(cinetpay_payment)

        return payment
    
    @staticmethod
    def check_payment_status_sync(session : Session, payment : Payment):
        if payment.payment_type == "CinetPayPayment":
            print("CinetPayPayment",payment.transaction_id)
        
            cinetpay_statement = (
                select(CinetPayPayment).where(CinetPayPayment.transaction_id == payment.transaction_id)
                )
            cinetpay_payment = session.exec(cinetpay_statement).first()
            
            if cinetpay_payment is None:
                print("CinetPayPayment not found")
                
                payment.status = PaymentStatusEnum.ERROR
                session.commit()
            else :
                result =   CinetPayService.check_cinetpay_payment_status_sync(payment.transaction_id)
                print("result",result)
                
                # Gérer les différents statuts selon la documentation CinetPay
                transaction_status = result["data"].get("status", "")
                
                if transaction_status == "ACCEPTED":
                    print("ACCEPTED")
                    payment.status = PaymentStatusEnum.ACCEPTED.value
                    cinetpay_payment.status = PaymentStatusEnum.ACCEPTED.value
                    cinetpay_payment.amount_received = float(result["data"].get("amount", 0))
                    cinetpay_payment.payment_method = result["data"].get("payment_method", "")
                    
                    if payment.payable_type == "JobApplication":
                        
                        job_application_statement = (
                            select(JobApplication).where(JobApplication.id == int(payment.payable_id))
                            )
                        job_application = session.exec(job_application_statement).first()
                        job_application.payment_id = payment.id
                        session.commit()
                        session.refresh(job_application)
                        # Créer automatiquement un compte utilisateur pour le candidat
                        PaymentService._create_job_application_user_sync_static(job_application, session)
                    
                    elif payment.payable_type == "StudentApplication":
                        statement = select(StudentApplication).where(StudentApplication.id == int(payment.payable_id))
                        student_application = session.exec(statement).first()
                        student_application.payment_id = payment.id
                        session.commit()
                        
                    elif payment.payable_type == "TrainingFeeInstallmentPayment" :
                        training_fee_installment_payment_statement = (
                            select(TrainingFeeInstallmentPayment).where(TrainingFeeInstallmentPayment.id == int(payment.payable_id))
                            )
                        training_fee_installment_payment = session.exec(training_fee_installment_payment_statement).first()
                        training_fee_installment_payment.payment_id = payment.id
                        session.commit()
                    
                    elif payment.payable_type == "CabinetApplication":
                        from src.api.cabinet.models import CabinetApplication, PaymentStatus
                        from datetime import datetime
                        cabinet_application_statement = (
                            select(CabinetApplication).where(CabinetApplication.id == payment.payable_id)
                        )
                        cabinet_application = session.exec(cabinet_application_statement).first()
                        if cabinet_application:
                            cabinet_application.payment_id = payment.id
                            cabinet_application.payment_status = PaymentStatus.PAID
                            cabinet_application.payment_date = datetime.utcnow()
                            session.commit()
                            session.refresh(cabinet_application)
                            print(f"✅ CabinetApplication {payment.payable_id} mis à jour avec payment_id: {payment.id}")
                    
                elif transaction_status in ["REFUSED", "CANCELLED"]:
                    payment.status = PaymentStatusEnum.REFUSED.value
                    cinetpay_payment.status = PaymentStatusEnum.REFUSED.value
                    cinetpay_payment.error_code = result.get("code", "")
                elif transaction_status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", 
                                            "WAITING_CUSTOMER_PAYMENT", "WAITING_CUSTOMER_OTP_CODE"]:
                    # Paiement en attente de confirmation
                    payment.status = PaymentStatusEnum.PENDING.value
                    cinetpay_payment.status = PaymentStatusEnum.PENDING.value
                
                session.commit()

        return payment
    

class CinetPayService:
    # Codes d'erreur selon la documentation CinetPay
    ERROR_CODES = {
        "00": "SUCCES",
        "201": "CREATED",
        "600": "PAYMENT_FAILED",
        "602": "INSUFFICIENT_BALANCE",
        "604": "OTP_CODE_ERROR",
        "608": "MINIMUM_REQUIRED_FIELDS",
        "606": "INCORRECT_SETTINGS",
        "609": "AUTH_NOT_FOUND",
        "623": "WAITING_CUSTOMER_TO_VALIDATE",
        "624": "PROCESSING_ERROR",
        "625": "ABONNEMENT_OR_TRANSACTIONS_EXPIRED",
        "627": "TRANSACTION_CANCEL",
        "662": "WAITING_CUSTOMER_PAYMENT",
        "663": "WAITING_CUSTOMER_OTP_CODE"
    }
    
    def __init__(self, session: AsyncSession = Depends(get_session_async)) -> None:
        self.session = session
    
    @staticmethod
    def get_error_message(error_code: str) -> str:
        """Retourne le message d'erreur selon le code CinetPay"""
        return CinetPayService.ERROR_CODES.get(error_code, "UNKNOWN_ERROR")


    async def initiate_cinetpay_payment(self, payment_data: CinetPayInit):
        
        # Validation des paramètres CinetPay
        print(f"=== CINETPAY CONFIGURATION CHECK ===")
        print(f"API Key: {settings.CINETPAY_API_KEY}")
        print(f"Site ID: {settings.CINETPAY_SITE_ID}")
        print(f"Notify URL: {settings.CINETPAY_NOTIFY_URL}")
        print(f"Return URL: {settings.CINETPAY_RETURN_URL}")
        print(f"Payment Amount: {payment_data.amount}")
        print(f"Payment Currency: {payment_data.currency}")
        print(f"Transaction ID: {payment_data.transaction_id}")
        
        # Vérification des paramètres requis (chargés depuis .env)
        if not settings.CINETPAY_API_KEY or settings.CINETPAY_API_KEY.strip() == "":
            error_msg = "CinetPay API Key is not configured. Please set CINETPAY_API_KEY in your .env file"
            print(f"ERROR: {error_msg}")
            return {
                "status": "error",
                "code": "INVALID_API_KEY",
                "message": error_msg
            }
        
        if not settings.CINETPAY_SITE_ID or settings.CINETPAY_SITE_ID.strip() == "":
            error_msg = "CinetPay Site ID is not configured. Please set CINETPAY_SITE_ID in your .env file"
            print(f"ERROR: {error_msg}")
            return {
                "status": "error",
                "code": "INVALID_SITE_ID",
                "message": error_msg
            }
        
        if payment_data.amount <= 0:
            error_msg = "Payment amount must be greater than 0"
            print(f"ERROR: {error_msg}")
            return {
                "status": "error",
                "code": "INVALID_AMOUNT",
                "message": error_msg
            }
        
        # Validation des montants selon la documentation CinetPay
        # Le montant doit être un multiple de 5 (sauf pour USD)
        original_amount = payment_data.amount
        if payment_data.currency != "USD":
            if payment_data.amount % 5 != 0:
                # Arrondir au multiple de 5 supérieur
                payment_data.amount = PaymentService.round_up_to_nearest_5(payment_data.amount)
                print(f"Amount rounded from {original_amount} to nearest multiple of 5: {payment_data.amount}")
        
        # S'assurer que le montant est un entier (comme dans les tests qui fonctionnent)
        payment_data.amount = int(payment_data.amount)
        
        # Validation des montants minimum et maximum selon la devise
        min_amounts = {
            "XOF": 100,  # Côte d'Ivoire, Sénégal, Togo, Bénin, Mali, Burkina Faso
            "XAF": 100,  # Cameroun
            "CDF": 100,  # RD Congo
            "GNF": 1000,  # Guinée
            "USD": 1  # USD (pas de restriction de multiple de 5)
        }
        
        max_amounts = {
            "XOF": 2000000,  # Maximum selon la documentation
            "XAF": 1500000,  # Cameroun
            "CDF": 2000000,  # RD Congo
            "GNF": 15000000,  # Guinée
            "USD": 3000  # RD Congo USD
        }
        
        min_amount = min_amounts.get(payment_data.currency, 100)
        max_amount = max_amounts.get(payment_data.currency, 2000000)
        
        if payment_data.amount < min_amount:
            error_msg = f"Montant minimum requis: {min_amount} {payment_data.currency}"
            print(f"ERROR: {error_msg}")
            return {
                "status": "error",
                "code": "AMOUNT_TOO_LOW",
                "message": error_msg
            }
        
        if payment_data.amount > max_amount:
            error_msg = f"Montant maximum autorisé: {max_amount} {payment_data.currency}"
            print(f"ERROR: {error_msg}")
            return {
                "status": "error",
                "code": "AMOUNT_TOO_HIGH",
                "message": error_msg
            }

        # Utiliser les canaux de paiement configurés selon la documentation CinetPay
        # Options: "ALL", "MOBILE_MONEY", "CREDIT_CARD", "WALLET"
        if payment_data.channels:
            channels_param = payment_data.channels.upper()
            # Valider que le channel est valide
            valid_channels = ["ALL", "MOBILE_MONEY", "CREDIT_CARD", "WALLET"]
            if channels_param not in valid_channels:
                channels_param = "ALL"
        else:
            channels_param = settings.CINETPAY_CHANNELS if settings.CINETPAY_CHANNELS else "ALL"
        
        print(f"CinetPay Channels: {channels_param}")
        print(f"CinetPay Card Payments Enabled: {settings.CINETPAY_ENABLE_CARD_PAYMENTS}")
        
        # Nettoyer la description pour retirer les caractères spéciaux non autorisés par CinetPay
        # La description a déjà été nettoyée dans initiate_payment, mais on la nettoie à nouveau ici
        # pour être sûr qu'elle ne contient aucun caractère spécial qui pourrait bloquer la validation
        original_description = payment_data.description or ""
        cleaned_description = clean_payment_description(original_description)
        print(f"=== DESCRIPTION CLEANING (FINAL CHECK) ===")
        print(f"Original: {original_description}")
        print(f"Cleaned: {cleaned_description}")
        print(f"Length: {len(cleaned_description)} characters")
        pattern = r'[^a-zA-Z0-9\s\-.]'
        has_special_chars = bool(re.search(pattern, cleaned_description))
        print(f"Contains special chars: {has_special_chars}")
        
        # Construire le payload selon la documentation CinetPay (identique aux tests qui fonctionnent)
        payload = {
            "amount": payment_data.amount,
            "currency": payment_data.currency,
            "description": cleaned_description,
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": payment_data.transaction_id,
            "channels": channels_param,
            "return_url": settings.CINETPAY_RETURN_URL,
            "notify_url": settings.CINETPAY_NOTIFY_URL,
            "metadata": clean_cinetpay_string(payment_data.meta or "", max_length=200) if payment_data.meta else "",
            "invoice_data": {
                "Service": clean_cinetpay_string("LAFAOM-MAO", max_length=50),
                "Montant": f"{payment_data.amount} {payment_data.currency}",
                "Reference": payment_data.transaction_id[:20]  # Limiter à 20 caractères
            },
            "lang": payment_data.lang or "fr",  # Langue du guichet de paiement (fr, en)
        }
        
        # Ajouter lock_phone_number si activé (selon la documentation)
        if payment_data.lock_phone_number:
            payload["lock_phone_number"] = True
        
        # Informations client OBLIGATOIRES pour activer l'option carte bancaire.
        # Selon la documentation CinetPay, toutes ces informations sont requises
        # IMPORTANT: Ces données sont utilisées par CinetPay pour configurer l'authentification de la carte
        # Nettoyer tous les champs pour éviter les caractères spéciaux
        payload["customer_name"] = clean_cinetpay_string(payment_data.customer_name or "Client", max_length=100)
        payload["customer_surname"] = clean_cinetpay_string(payment_data.customer_surname or "LAFAOM", max_length=100)
        payload["customer_email"] = (payment_data.customer_email or "client@lafaom.com").strip()  # Email ne doit pas être nettoyé de la même manière
        
        # Formater le numéro de téléphone selon la documentation CinetPay
        # IMPORTANT: Pour le paiement par carte bancaire, le numéro de téléphone est OBLIGATOIRE
        # Support pour lock_phone_number selon la documentation
        if payment_data.customer_phone_number:
            phone = payment_data.customer_phone_number.strip()
            # Si le numéro commence par +, on le garde tel quel
            if not phone.startswith("+"):
                # Déterminer le préfixe selon le pays
                country_prefix = "237"  # Cameroun par défaut (XAF)
                if payment_data.currency == "XOF":
                    country_prefix = "221"  # Sénégal par défaut
                elif payment_data.customer_country:
                    # Mapper les codes pays aux préfixes
                    country_prefixes = {
                        "SN": "221", "CI": "225", "TG": "228", "BJ": "229",
                        "ML": "223", "BF": "226", "CM": "237", "CD": "243", "GN": "224"
                    }
                    country_prefix = country_prefixes.get(payment_data.customer_country.upper(), "237")
                
                if phone.startswith(country_prefix):
                    phone = "+" + phone
                elif phone.startswith("0"):
                    phone = "+" + country_prefix + phone[1:]
                else:
                    phone = "+" + country_prefix + phone
            
            payload["customer_phone_number"] = phone
        else:
            # Pour le paiement par carte bancaire, un numéro de téléphone valide est OBLIGATOIRE
            # Générer un numéro par défaut valide selon le pays
            # Déterminer le préfixe selon la devise ou le pays
            if payment_data.currency == "XAF":
                default_prefix = "237"  # Cameroun
                default_phone = "657807309"  # Format valide pour le Cameroun
            elif payment_data.currency == "XOF":
                default_prefix = "221"  # Sénégal
                default_phone = "771234567"  # Format valide pour le Sénégal
            elif payment_data.customer_country:
                country_prefixes = {
                    "SN": "221", "CI": "225", "TG": "228", "BJ": "229",
                    "ML": "223", "BF": "226", "CM": "237", "CD": "243", "GN": "224"
                }
                default_prefix = country_prefixes.get(payment_data.customer_country.upper(), "237")
                default_phone = "657807309"  # Format par défaut
            else:
                default_prefix = "237"
                default_phone = "657807309"
            
            payload["customer_phone_number"] = f"+{default_prefix}{default_phone}"
            print(f"⚠️  Aucun numéro de téléphone fourni, utilisation du numéro par défaut: {payload['customer_phone_number']}")
        
        # S'assurer que tous les champs obligatoires sont remplis
        # Adapter les valeurs par défaut selon la devise/pays
        if payment_data.currency == "XAF":
            default_address = "Yaoundé"
            default_city = "Yaoundé"
        else:
            default_address = "Dakar"
            default_city = "Dakar"
        
        payload["customer_address"] = clean_cinetpay_string(payment_data.customer_address or default_address, max_length=200)
        payload["customer_city"] = clean_cinetpay_string(payment_data.customer_city or default_city, max_length=100)
        
        # Code pays - déterminer selon la devise ou le pays fourni
        if payment_data.customer_country:
            country_code = payment_data.customer_country.upper().strip()
            # Mapper les noms de pays aux codes ISO
            country_mapping = {
                "SENEGAL": "SN", "SN": "SN",
                "COTE D'IVOIRE": "CI", "IVOIRE": "CI", "CI": "CI",
                "TOGO": "TG", "TG": "TG",
                "BENIN": "BJ", "BJ": "BJ",
                "MALI": "ML", "ML": "ML",
                "BURKINA FASO": "BF", "BF": "BF",
                "CAMEROUN": "CM", "CM": "CM",
                "CONGO": "CD", "RDC": "CD", "CD": "CD",
                "GUINEE": "GN", "GN": "GN"
            }
            payload["customer_country"] = country_mapping.get(country_code, "CM")  # Cameroun par défaut
        else:
            # Déterminer le pays selon la devise
            currency_to_country = {
                "XOF": "SN",  # Sénégal par défaut pour XOF
                "XAF": "CM",  # Cameroun pour XAF
                "CDF": "CD",  # RD Congo pour CDF
                "GNF": "GN",  # Guinée pour GNF
                "USD": "CD"   # RD Congo USD
            }
            payload["customer_country"] = currency_to_country.get(payment_data.currency, "CM")
            
        # State - utiliser le code pays (selon la documentation, c'est le code ISO du pays)
        payload["customer_state"] = payload["customer_country"]
            
        # Code postal - valeur par défaut si non fourni
        if payment_data.customer_zip_code:
            payload["customer_zip_code"] = str(payment_data.customer_zip_code).strip()[:10]  # Limiter à 10 caractères
        else:
            payload["customer_zip_code"] = "065100"
        
        # Vérification finale : s'assurer qu'aucun champ obligatoire n'est vide
        # IMPORTANT: Pour le paiement par carte bancaire, tous les champs doivent être valides
        required_fields = ["customer_name", "customer_surname", "customer_email", "customer_phone_number", 
                          "customer_address", "customer_city", "customer_country", "customer_state", "customer_zip_code"]
        for field in required_fields:
            if not payload.get(field) or (isinstance(payload[field], str) and payload[field].strip() == ""):
                print(f"⚠️  WARNING: Field {field} is empty, using default value")
                if field == "customer_name":
                    payload[field] = "Client"
                elif field == "customer_surname":
                    payload[field] = "LAFAOM"
                elif field == "customer_email":
                    payload[field] = "client@lafaom.com"
                elif field == "customer_phone_number":
                    # Utiliser le même format que défini précédemment
                    if payment_data.currency == "XAF":
                        payload[field] = "+237657807309"
                    else:
                        payload[field] = "+221771234567"
                elif field == "customer_address":
                    payload[field] = "Yaoundé" if payment_data.currency == "XAF" else "Dakar"
                elif field == "customer_city":
                    payload[field] = "Yaoundé" if payment_data.currency == "XAF" else "Dakar"
                elif field == "customer_state":
                    payload[field] = payload.get("customer_country", "CM")
                elif field == "customer_country":
                    payload[field] = "CM" if payment_data.currency == "XAF" else "SN"
                elif field == "customer_zip_code":
                    payload[field] = "065100"
        
        # Logs détaillés pour le diagnostic (surtout pour le paiement par carte bancaire)
        if channels_param == "CREDIT_CARD":
            print(f"\n{'='*80}")
            print(f"📋 PAYLOAD CINETPAY - PAIEMENT CARTE BANCAIRE")
            print(f"{'='*80}")
            print(f"Transaction ID: {payment_data.transaction_id}")
            print(f"Amount: {payload['amount']} {payload['currency']}")
            print(f"Channels: {channels_param}")
            print(f"\n👤 INFORMATIONS CLIENT:")
            print(f"  - Name: {payload['customer_name']}")
            print(f"  - Surname: {payload['customer_surname']}")
            print(f"  - Email: {payload['customer_email']}")
            print(f"  - Phone: {payload['customer_phone_number']}")
            print(f"  - Address: {payload['customer_address']}")
            print(f"  - City: {payload['customer_city']}")
            print(f"  - Country: {payload['customer_country']}")
            print(f"  - State: {payload['customer_state']}")
            print(f"  - Zip Code: {payload['customer_zip_code']}")
            print(f"{'='*80}\n")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Headers selon les tests qui fonctionnent
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "LAFAOM-Backend/1.0"
            }
            
            # Logs détaillés pour debug (identique aux tests)
            print(f"=== CINETPAY API REQUEST ===")
            print(f"URL: https://api-checkout.cinetpay.com/v2/payment")
            print(f"Transaction ID: {payment_data.transaction_id}")
            print(f"Transaction ID length: {len(payment_data.transaction_id)}")
            print(f"Amount: {payload['amount']} {payload['currency']}")
            print(f"Channels: {payload['channels']}")
            print(f"Description: {payload['description'][:50]}...")
            
            try:
                response = await client.post(
                    "https://api-checkout.cinetpay.com/v2/payment", 
                    json=payload,
                    headers=headers
                )
            except httpx.TimeoutException as timeout_error:
                print(f"CinetPay API Timeout: {timeout_error}")
                return {
                    "status": "error",
                    "code": "TIMEOUT",
                    "message": f"CinetPay API timeout: {str(timeout_error)}"
                }
            except httpx.ConnectError as connect_error:
                print(f"CinetPay API Connection Error: {connect_error}")
                return {
                    "status": "error",
                    "code": "CONNECTION_ERROR",
                    "message": f"CinetPay API connection failed: {str(connect_error)}"
                }
            except Exception as http_error:
                print(f"CinetPay API HTTP Error: {http_error}")
                return {
                    "status": "error",
                    "code": "HTTP_ERROR",
                    "message": f"CinetPay API error: {str(http_error)}"
                }
            
            print(f"=== CINETPAY API RESPONSE ===")
            print(f"Status Code: {response.status_code}")
            
            try:
                response_data = response.json()
                response_code = response_data.get("code", "")
                response_message = response_data.get("message", "")
                print(f"Code CinetPay: {response_code}")
                print(f"Message: {response_message}")
            except json.JSONDecodeError as json_error:
                print(f"❌ Failed to parse JSON response: {json_error}")
                print(f"Raw response text: {response.text[:500]}")
                return {
                    "status": "error",
                    "code": "INVALID_JSON_RESPONSE",
                    "message": f"Invalid JSON response from CinetPay: {response.text[:500]}"
                }
            
            if response.status_code != 200:
                error_message = f"HTTP Error {response.status_code}: {response_data.get('message', 'Unknown error')}"
                error_description = response_data.get('description', '')
                if error_description:
                    error_message += f" - {error_description}"
                print(f"❌ HTTP Error: {error_message}")
                return {
                    "status": "error",
                    "code": response_data.get("code", f"HTTP_{response.status_code}"),
                    "message": error_message
                }
            
            # Gérer les différents codes de réponse selon la documentation CinetPay
            response_code = response_data.get("code")
            
            if response_code == "201":  # Transaction créée avec succès
                payment_url = response_data["data"]["payment_url"]
                payment_token = response_data["data"].get("payment_token", "")
                api_response_id = response_data.get("api_response_id", "")
                
                # Créer l'enregistrement CinetPayPayment (identique aux tests qui fonctionnent)
                db_payment = CinetPayPayment(
                    transaction_id=payment_data.transaction_id,
                    amount=payment_data.amount,
                    currency=payment_data.currency,
                    status="PENDING",
                    payment_url=payment_url,
                    payment_token=payment_token,
                    api_response_id=api_response_id
                )

                self.session.add(db_payment)
                await self.session.commit()
                await self.session.refresh(db_payment)
                return {
                    "status": "success",
                    "data": db_payment
                }
            else:
                # Gérer les erreurs selon les codes de la documentation
                error_code = str(response_data.get("code", "UNKNOWN_ERROR"))
                error_message = response_data.get("message", "Unknown error")
                error_description = response_data.get("description", "")
                
                # Obtenir le message d'erreur standardisé
                standard_message = CinetPayService.get_error_message(error_code)
                
                print(f"CinetPay Error - Code: {error_code}, Message: {error_message}, Description: {error_description}")
                print(f"Standard Error Message: {standard_message}")
                
                # Construire le message d'erreur détaillé
                detailed_message = error_message
                if error_description:
                    detailed_message = f"{error_message}: {error_description}"
                elif standard_message != "UNKNOWN_ERROR":
                    detailed_message = f"{standard_message}: {error_message}"
                
                return {
                    "status": "error",
                    "code": error_code,
                    "message": detailed_message,
                    "standard_message": standard_message
                }

    async def initiate_cinetpay_swallow_payment(self, payment_data: CinetPayInit):
        db_payment = CinetPayPayment(
                    
                transaction_id=payment_data.transaction_id,
                amount=payment_data.amount,
                currency=payment_data.currency,
                status="PENDING",
            )

        self.session.add(db_payment)
        await self.session.commit()
        await self.session.refresh(db_payment)
        return db_payment

    @staticmethod
    async def check_cinetpay_payment_status(transaction_id: str):
        """
        Vérifie le statut d'une transaction CinetPay
        
        Retourne:
        - code "00": SUCCES
        - code "627": TRANSACTION_CANCEL
        - Autres codes d'erreur selon la documentation
        """
        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "https://api-checkout.cinetpay.com/v2/payment/check", 
                    json=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "LAFAOM-Backend/1.0"}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error checking CinetPay payment status: {e}")
                raise
        
    
    @staticmethod
    def check_cinetpay_payment_status_sync(transaction_id: str):
        """
        Vérifie le statut d'une transaction CinetPay (version synchrone)
        
        Retourne:
        - code "00": SUCCES
        - code "627": TRANSACTION_CANCEL
        - Autres codes d'erreur selon la documentation
        """
        payload = {
            "apikey": settings.CINETPAY_API_KEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id
        }
        # Using synchronous HTTP client
        with httpx.Client(timeout=30.0) as client:
            try:
                response = client.post(
                    "https://api-checkout.cinetpay.com/v2/payment/check",
                    json=payload,
                    headers={"Content-Type": "application/json", "User-Agent": "LAFAOM-Backend/1.0"}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"Error checking CinetPay payment status (sync): {e}")
                raise

    async def get_cinetpay_payment(self, transaction_id: str):
        statement = select(CinetPayPayment).where(CinetPayPayment.transaction_id == transaction_id)
        cinetpay_payment = await self.session.execute(statement)
        
        return cinetpay_payment.scalars().first()
    
    @staticmethod
    def _create_job_application_user_sync_static(job_application: JobApplication, session: Session) -> None:
        """Créer un compte utilisateur pour le candidat d'emploi après paiement confirmé (version synchrone)"""
        try:
            # Générer un nom d'utilisateur unique
            username = f"candidate_{job_application.first_name.lower()}_{job_application.last_name.lower()}_{job_application.id}"
            
            # Générer un mot de passe temporaire
            temp_password = PaymentService._generate_temp_password_static()
            
            # Créer l'utilisateur directement
            from src.api.user.models import User
            from datetime import datetime
            
            user = User(
                first_name=job_application.first_name,
                last_name=job_application.last_name,
                email=job_application.email,
                mobile_number=job_application.phone_number,
                status=UserStatusEnum.ACTIVE,
                user_type=UserTypeEnum.STUDENT,
                two_factor_enabled=False,
                web_token=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Hasher le mot de passe
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            user.password_hash = pwd_context.hash(temp_password)
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Mettre à jour la candidature avec l'ID utilisateur
            job_application.user_id = user.id
            session.commit()
            
            # Envoyer les identifiants par email (version synchrone)
            PaymentService._send_job_application_credentials_email_sync_static(job_application, username, temp_password)
            
            print(f"Compte utilisateur créé pour le candidat {job_application.first_name} {job_application.last_name}")
            
        except Exception as e:
            print(f"Erreur lors de la création du compte utilisateur pour la candidature d'emploi: {e}")
            raise e

    @staticmethod
    def _generate_temp_password_static(length: int = 12) -> str:
        """Générer un mot de passe temporaire"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))

    @staticmethod
    def _send_job_application_credentials_email_sync_static(job_application: JobApplication, username: str, password: str) -> None:
        """Envoyer les identifiants par email pour les candidatures d'emploi (version synchrone)"""
        try:
            from src.helper.notifications import JobApplicationCredentialsNotification
            
            # Créer la notification directement
            notification = JobApplicationCredentialsNotification(
                email=job_application.email,
                username=username,
                temporary_password=password,
                candidate_name=f"{job_application.first_name} {job_application.last_name}",
                login_url=f"{settings.BASE_URL}/auth/login"
            )
            
            # Envoyer l'email avec les identifiants
            notification.send_notification()
            
            print(f"Identifiants envoyés par email à {job_application.email}")
            
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {e}")
            raise e

