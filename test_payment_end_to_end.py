"""
Tests end-to-end pour simuler un paiement complet jusqu'à la validation
Ces tests peuvent être exécutés avec pytest ou directement
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from src.api.payments.service import PaymentService, CinetPayService
from src.api.payments.schemas import PaymentInitInput
from src.api.payments.models import Payment, CinetPayPayment, PaymentStatusEnum


# Informations de test fournies
MOBILE_PHONE = "+237657807309"
CARD_NUMBER = "4834 5600 7033 2785"
CARD_EXPIRY = "05/26"
CARD_CVV = "329"


class MockPayable:
    """Mock d'un objet payable pour les tests"""
    def __init__(self, id: str, class_name: str = "StudentApplication"):
        self.id = id
        self.__class__.__name__ = class_name


class MockAsyncSession:
    """Mock d'une session async pour les tests"""
    def __init__(self):
        self.added = []
        self.committed = False
        self.payments = {}
        self.cinetpay_payments = {}
    
    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, Payment):
            self.payments[obj.transaction_id] = obj
        elif isinstance(obj, CinetPayPayment):
            self.cinetpay_payments[obj.transaction_id] = obj
    
    async def commit(self):
        self.committed = True
    
    async def refresh(self, obj):
        pass
    
    async def execute(self, stmt):
        result = MagicMock()
        result.scalars.return_value.first.return_value = None
        return result


@pytest.fixture
def mock_session():
    """Fixture pour créer une session mock"""
    return MockAsyncSession()


@pytest.fixture
def payment_service(mock_session):
    """Fixture pour le service de paiement"""
    service = PaymentService(session=mock_session)
    return service


@pytest.fixture
def mock_cinetpay_init_response():
    """Mock de la réponse d'initialisation CinetPay"""
    return {
        "code": "201",
        "message": "CREATED",
        "description": "Transaction created with success",
        "data": {
            "payment_token": "test_payment_token_12345",
            "payment_url": "https://checkout.cinetpay.com/payment/test_payment_token_12345"
        },
        "api_response_id": "1234567890.1234"
    }


@pytest.fixture
def mock_cinetpay_status_pending():
    """Mock du statut en attente"""
    return {
        "code": "623",
        "message": "WAITING_CUSTOMER_TO_VALIDATE",
        "data": {
            "amount": "10000",
            "currency": "XAF",
            "status": "WAITING_FOR_CUSTOMER",
            "payment_method": None,
            "description": "Test paiement",
            "metadata": None,
            "operator_id": None,
            "payment_date": "",
            "fund_availability_date": ""
        },
        "api_response_id": "1234567890.1234"
    }


@pytest.fixture
def mock_cinetpay_status_accepted():
    """Mock du statut accepté"""
    return {
        "code": "00",
        "message": "SUCCES",
        "data": {
            "amount": "10000",
            "currency": "XAF",
            "status": "ACCEPTED",
            "payment_method": "OM",
            "description": "Test paiement",
            "metadata": None,
            "operator_id": "MP220915.2257.A76307",
            "payment_date": "2024-01-15 10:30:00",
            "fund_availability_date": "2024-01-17 00:00:00"
        },
        "api_response_id": "1234567890.1234"
    }


class TestMobileMoneyPaymentFlow:
    """Test du flux complet de paiement Mobile Money"""
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_mobile_money_payment_flow(
        self,
        mock_client_class,
        payment_service,
        mock_session,
        mock_cinetpay_init_response,
        mock_cinetpay_status_pending,
        mock_cinetpay_status_accepted
    ):
        """Test complet du flux de paiement Mobile Money jusqu'à la validation"""
        print("\n" + "="*80)
        print("TEST: PAIEMENT MOBILE MONEY - FLUX COMPLET")
        print("="*80)
        print(f"Numéro: {MOBILE_PHONE}")
        print("-"*80)
        
        # Créer un objet payable
        payable = MockPayable(str(uuid.uuid4()), "StudentApplication")
        
        # Créer les données de paiement
        payment_data = PaymentInitInput(
            payable=payable,
            amount=10000.0,
            product_currency="XAF",
            description="Test paiement Mobile Money complet",
            payment_provider="CINETPAY",
            customer_name="Test",
            customer_surname="User",
            customer_email="test@example.com",
            customer_phone_number=MOBILE_PHONE,
            customer_address="Yaoundé",
            customer_city="Yaoundé",
            customer_country="CM",
            customer_state="CM",
            customer_zip_code="065100",
            channels="MOBILE_MONEY",
            lang="fr"
        )
        
        # Mock de la réponse HTTP pour l'initialisation
        mock_init_response = MagicMock()
        mock_init_response.status_code = 200
        mock_init_response.json.return_value = mock_cinetpay_init_response
        mock_init_response.headers = {}
        mock_init_response.text = json.dumps(mock_cinetpay_init_response)
        
        # Mock de la réponse HTTP pour la vérification (d'abord en attente, puis accepté)
        mock_status_responses = [
            mock_cinetpay_status_pending,  # Première vérification: en attente
            mock_cinetpay_status_accepted  # Deuxième vérification: accepté
        ]
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        # Configurer les réponses mock
        async def mock_post(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            
            if "payment" in url and "check" not in url:
                # Initialisation
                mock_response.json.return_value = mock_cinetpay_init_response
                mock_response.text = json.dumps(mock_cinetpay_init_response)
            else:
                # Vérification du statut
                if mock_status_responses:
                    response_data = mock_status_responses.pop(0)
                    mock_response.json.return_value = response_data
                    mock_response.text = json.dumps(response_data)
                else:
                    # Par défaut, retourner accepté
                    mock_response.json.return_value = mock_cinetpay_status_accepted
                    mock_response.text = json.dumps(mock_cinetpay_status_accepted)
            
            return mock_response
        
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client_class.return_value = mock_client
        
        # Étape 1: Initialisation du paiement
        print("\n[Étape 1/3] Initialisation du paiement...")
        result = await payment_service.initiate_payment(payment_data)
        
        assert result.get("success") is True, f"L'initialisation a échoué: {result.get('message')}"
        transaction_id = result.get("transaction_id")
        payment_link = result.get("payment_link")
        
        print(f"✅ Paiement initialisé")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Lien: {payment_link}")
        
        # Étape 2: Vérification du statut (en attente)
        print("\n[Étape 2/3] Vérification du statut (simulation: en attente)...")
        print(f"   → L'utilisateur doit valider sur {MOBILE_PHONE}")
        
        # Simuler la vérification du statut
        status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
        status = status_result.get("data", {}).get("status", "")
        
        assert status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", "PENDING"], \
            f"Statut inattendu: {status}"
        
        print(f"⏳ Statut: {status} (en attente de validation)")
        
        # Étape 3: Vérification du statut (accepté après validation)
        print("\n[Étape 3/3] Vérification du statut (simulation: accepté)...")
        print("   → L'utilisateur a validé le paiement")
        
        status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
        status = status_result.get("data", {}).get("status", "")
        code = status_result.get("code", "")
        
        assert code == "00" and status == "ACCEPTED", \
            f"Le paiement devrait être accepté, mais statut: {status}, code: {code}"
        
        print(f"✅ Paiement accepté!")
        print(f"   Statut: {status}")
        print(f"   Méthode: {status_result.get('data', {}).get('payment_method', 'N/A')}")
        print(f"   Montant: {status_result.get('data', {}).get('amount', 0)} {status_result.get('data', {}).get('currency', '')}")
        
        print("\n" + "="*80)
        print("✅ TEST RÉUSSI: Flux Mobile Money complet")
        print("="*80)


class TestCreditCardPaymentFlow:
    """Test du flux complet de paiement par carte bancaire"""
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_credit_card_payment_flow(
        self,
        mock_client_class,
        payment_service,
        mock_session,
        mock_cinetpay_init_response,
        mock_cinetpay_status_pending,
        mock_cinetpay_status_accepted
    ):
        """Test complet du flux de paiement par carte bancaire jusqu'à la validation"""
        print("\n" + "="*80)
        print("TEST: PAIEMENT CARTE BANCAIRE - FLUX COMPLET")
        print("="*80)
        print(f"Carte: {CARD_NUMBER}")
        print(f"Expiration: {CARD_EXPIRY}")
        print(f"CVV: {CARD_CVV}")
        print("-"*80)
        
        # Créer un objet payable
        payable = MockPayable(str(uuid.uuid4()), "StudentApplication")
        
        # Créer les données de paiement
        payment_data = PaymentInitInput(
            payable=payable,
            amount=10000.0,
            product_currency="XAF",
            description="Test paiement Carte Bancaire complet",
            payment_provider="CINETPAY",
            customer_name="Test",
            customer_surname="User",
            customer_email="test@example.com",
            customer_phone_number="+237657807309",
            customer_address="Yaoundé",
            customer_city="Yaoundé",
            customer_country="CM",
            customer_state="CM",
            customer_zip_code="065100",
            channels="CREDIT_CARD",
            lang="fr"
        )
        
        # Mock de la réponse HTTP
        mock_init_response = MagicMock()
        mock_init_response.status_code = 200
        mock_init_response.json.return_value = mock_cinetpay_init_response
        mock_init_response.headers = {}
        mock_init_response.text = json.dumps(mock_cinetpay_init_response)
        
        # Modifier le statut accepté pour indiquer une carte bancaire
        mock_cinetpay_status_accepted_card = mock_cinetpay_status_accepted.copy()
        mock_cinetpay_status_accepted_card["data"]["payment_method"] = "VISAM"
        
        mock_status_responses = [
            mock_cinetpay_status_pending,
            mock_cinetpay_status_accepted_card
        ]
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        async def mock_post(url, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            
            if "payment" in url and "check" not in url:
                mock_response.json.return_value = mock_cinetpay_init_response
                mock_response.text = json.dumps(mock_cinetpay_init_response)
            else:
                if mock_status_responses:
                    response_data = mock_status_responses.pop(0)
                    mock_response.json.return_value = response_data
                    mock_response.text = json.dumps(response_data)
                else:
                    mock_response.json.return_value = mock_cinetpay_status_accepted_card
                    mock_response.text = json.dumps(mock_cinetpay_status_accepted_card)
            
            return mock_response
        
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client_class.return_value = mock_client
        
        # Étape 1: Initialisation
        print("\n[Étape 1/3] Initialisation du paiement...")
        result = await payment_service.initiate_payment(payment_data)
        
        assert result.get("success") is True, f"L'initialisation a échoué: {result.get('message')}"
        transaction_id = result.get("transaction_id")
        payment_link = result.get("payment_link")
        
        print(f"✅ Paiement initialisé")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Lien: {payment_link}")
        
        # Vérifier que tous les champs requis pour la carte sont présents
        call_args = mock_client.post.call_args_list[0]
        payload = call_args[1]["json"]
        
        required_fields = [
            "customer_name", "customer_surname", "customer_email",
            "customer_phone_number", "customer_address", "customer_city",
            "customer_country", "customer_zip_code"
        ]
        
        for field in required_fields:
            assert payload.get(field) is not None and payload[field] != "", \
                f"Le champ {field} est requis pour la carte bancaire"
        
        print(f"✅ Tous les champs requis pour la carte bancaire sont présents")
        
        # Étape 2: Vérification (en attente)
        print("\n[Étape 2/3] Vérification du statut (simulation: en attente)...")
        print(f"   → L'utilisateur doit compléter le formulaire de carte")
        print(f"   → Carte: {CARD_NUMBER}")
        print(f"   → Expiration: {CARD_EXPIRY}, CVV: {CARD_CVV}")
        
        status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
        status = status_result.get("data", {}).get("status", "")
        
        assert status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", "PENDING"], \
            f"Statut inattendu: {status}"
        
        print(f"⏳ Statut: {status} (en attente de validation)")
        
        # Étape 3: Vérification (accepté)
        print("\n[Étape 3/3] Vérification du statut (simulation: accepté)...")
        print("   → L'utilisateur a complété le paiement")
        
        status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
        status = status_result.get("data", {}).get("status", "")
        code = status_result.get("code", "")
        
        assert code == "00" and status == "ACCEPTED", \
            f"Le paiement devrait être accepté, mais statut: {status}, code: {code}"
        
        print(f"✅ Paiement accepté!")
        print(f"   Statut: {status}")
        print(f"   Méthode: {status_result.get('data', {}).get('payment_method', 'N/A')}")
        print(f"   Montant: {status_result.get('data', {}).get('amount', 0)} {status_result.get('data', {}).get('currency', '')}")
        
        print("\n" + "="*80)
        print("✅ TEST RÉUSSI: Flux Carte Bancaire complet")
        print("="*80)


if __name__ == "__main__":
    # Exécuter les tests avec pytest
    pytest.main([__file__, "-v", "-s"])

