"""
Tests pour les paiements CinetPay
Teste les trois méthodes de paiement : Mobile Money, Wallet et Carte Bancaire
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import json
import uuid
from datetime import datetime, timezone

from src.api.payments.service import PaymentService
from src.api.payments.schemas import PaymentInitInput
from src.api.user.models import User, Address
from src.api.training.models import StudentApplication, TrainingSession, Training


# Mock pour simuler une session async
class MockAsyncSession:
    def __init__(self):
        self.added = []
        self.committed = False
    
    def add(self, obj):
        self.added.append(obj)
    
    async def commit(self):
        self.committed = True
    
    async def refresh(self, obj):
        pass
    
    async def execute(self, stmt):
        result = MagicMock()
        result.scalars.return_value.first.return_value = None
        return result


@pytest.fixture
def mock_async_db():
    """Fixture pour créer une session async mock"""
    return MockAsyncSession()


@pytest.fixture
def payment_service(mock_async_db):
    """Fixture pour le service de paiement"""
    service = PaymentService(session=mock_async_db)
    return service


@pytest.fixture
def test_user():
    """Créer un utilisateur de test"""
    return User(
        id=str(uuid.uuid4()),
        first_name="John",
        last_name="Doe",
        email="john.doe@test.com",
        mobile_number="+221771234567",
        country_code="SN",
        password="hashed_password",
        status="ACTIVE",
        user_type="STUDENT"
    )


@pytest.fixture
def test_training_application(test_user):
    """Créer une candidature de formation de test"""
    training = Training(
        id=str(uuid.uuid4()),
        title="Formation Test",
        status="ACTIVE"
    )
    
    session = TrainingSession(
        id=str(uuid.uuid4()),
        training_id=training.id,
        registration_fee=10000.0,
        currency="XOF",
        status="ACTIVE"
    )
    
    application = StudentApplication(
        user_id=test_user.id,
        training_id=training.id,
        target_session_id=session.id,
        status="SUBMITTED",
        currency="XOF"
    )
    
    return application


@pytest.fixture
def mock_cinetpay_response_success():
    """Mock d'une réponse réussie de CinetPay"""
    return {
        "code": "201",
        "message": "Votre demande a été traitée avec succès",
        "data": {
            "payment_url": "https://checkout.cinetpay.com/payment/test123",
            "payment_token": "test_token_12345"
        },
        "api_response_id": "api_resp_123"
    }


class TestPaymentMobileMoney:
    """Tests pour les paiements Mobile Money"""
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_initiate_mobile_money_payment_success(
        self, 
        mock_client_class,
        payment_service,
        test_training_application,
        test_user,
        mock_cinetpay_response_success
    ):
        """Test d'initialisation réussie d'un paiement Mobile Money"""
        # Mock de la réponse HTTP
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_cinetpay_response_success
        mock_response.headers = {}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Créer l'input de paiement
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description="Test Mobile Money Payment",
            payment_provider="CINETPAY",
            payment_method="MOBILE_MONEY",
            customer_name=test_user.last_name,
            customer_surname=test_user.first_name,
            customer_email=test_user.email,
            customer_phone_number=test_user.mobile_number,
            customer_address="123 Rue Test",
            customer_city="Dakar",
            customer_country="SN"
        )
        
        # Exécuter le test
        result = await payment_service.initiate_payment(payment_input)
        
        # Vérifications
        assert result["success"] is True
        assert "payment_link" in result
        assert result["payment_link"] == "https://checkout.cinetpay.com/payment/test123"
        assert "transaction_id" in result
        
        # Vérifier que l'appel API a été fait avec les bons paramètres
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://api-checkout.cinetpay.com/v2/payment"
        
        payload = call_args[1]["json"]
        assert payload["amount"] == 10000.0
        # La devise peut être convertie automatiquement (XOF -> XAF)
        assert payload["currency"] in ["XOF", "XAF"]
        # Le code utilise "ALL" pour activer tous les canaux
        channels = payload.get("channels", "")
        assert channels == "ALL" or "MOBILE_MONEY" in channels
        assert payload["customer_phone_number"] == test_user.mobile_number


class TestPaymentWallet:
    """Tests pour les paiements Wallet"""
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_initiate_wallet_payment_success(
        self,
        mock_client_class,
        payment_service,
        test_training_application,
        test_user,
        mock_cinetpay_response_success
    ):
        """Test d'initialisation réussie d'un paiement Wallet"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_cinetpay_response_success
        mock_response.headers = {}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description="Test Wallet Payment",
            payment_provider="CINETPAY",
            payment_method="WALLET",
            customer_name=test_user.last_name,
            customer_surname=test_user.first_name,
            customer_email=test_user.email,
            customer_phone_number=test_user.mobile_number,
            customer_address="123 Rue Test",
            customer_city="Dakar",
            customer_country="SN"
        )
        
        result = await payment_service.initiate_payment(payment_input)
        
        assert result["success"] is True
        assert "payment_link" in result
        
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        # Le code utilise "ALL" pour activer tous les canaux
        assert payload.get("channels") == "ALL" or "WALLET" in payload.get("channels", "")


class TestPaymentCreditCard:
    """Tests pour les paiements par carte bancaire"""
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_initiate_credit_card_payment_success(
        self,
        mock_client_class,
        payment_service,
        test_training_application,
        test_user,
        mock_cinetpay_response_success
    ):
        """Test d'initialisation réussie d'un paiement par carte bancaire"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_cinetpay_response_success
        mock_response.headers = {}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description="Test Credit Card Payment",
            payment_provider="CINETPAY",
            payment_method="CREDIT_CARD",
            customer_name=test_user.last_name,
            customer_surname=test_user.first_name,
            customer_email=test_user.email,
            customer_phone_number=test_user.mobile_number,
            customer_address="123 Rue Test",
            customer_city="Dakar",
            customer_country="SN",
            customer_state="SN",
            customer_zip_code="065100"
        )
        
        result = await payment_service.initiate_payment(payment_input)
        
        assert result["success"] is True
        assert "payment_link" in result
        
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        
        # Vérifier que tous les champs obligatoires pour la carte sont présents
        assert payload["customer_name"] is not None
        assert payload["customer_surname"] is not None
        assert payload["customer_email"] is not None
        assert payload["customer_phone_number"] is not None
        assert payload["customer_address"] is not None
        assert payload["customer_city"] is not None
        assert payload["customer_country"] is not None
        assert payload["customer_zip_code"] is not None
        
        # Vérifier que CREDIT_CARD est dans les canaux ou que "ALL" est utilisé
        channels = payload.get("channels", "")
        assert channels == "ALL" or "CREDIT_CARD" in channels
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_initiate_credit_card_payment_with_defaults(
        self,
        mock_client_class,
        payment_service,
        test_training_application,
        mock_cinetpay_response_success
    ):
        """Test d'initialisation d'un paiement par carte avec valeurs par défaut"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_cinetpay_response_success
        mock_response.headers = {}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description="Test Credit Card Payment Defaults",
            payment_provider="CINETPAY",
            payment_method="CREDIT_CARD",
            # Informations client manquantes - doivent être remplacées par des valeurs par défaut
            customer_name=None,
            customer_surname=None,
            customer_email=None
        )
        
        result = await payment_service.initiate_payment(payment_input)
        
        # Le service doit utiliser des valeurs par défaut
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        
        # Vérifier que les valeurs par défaut sont utilisées
        assert payload["customer_name"] is not None and payload["customer_name"] != ""
        assert payload["customer_surname"] is not None and payload["customer_surname"] != ""
        assert payload["customer_email"] is not None and payload["customer_email"] != ""
        assert payload["customer_phone_number"] is not None and payload["customer_phone_number"] != ""
        assert payload["customer_address"] is not None and payload["customer_address"] != ""
        assert payload["customer_city"] is not None and payload["customer_city"] != ""
        assert payload["customer_country"] == "SN"
        assert payload["customer_zip_code"] is not None and payload["customer_zip_code"] != ""


class TestPaymentValidation:
    """Tests de validation des paiements"""
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_payment_description_cleaning(
        self,
        mock_client_class,
        payment_service,
        test_training_application,
        test_user,
        mock_cinetpay_response_success
    ):
        """Test que la description est nettoyée des caractères spéciaux"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_cinetpay_response_success
        mock_response.headers = {}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        # Description avec caractères spéciaux
        description = "Payment for training application fee of session Formation d'Auxiliaires de Vie en Univers Judiciaire (AVUJ) – January 2026"
        
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description=description,
            payment_provider="CINETPAY",
            payment_method="WALLET",
            customer_name=test_user.last_name,
            customer_surname=test_user.first_name,
            customer_email=test_user.email,
            customer_phone_number=test_user.mobile_number
        )
        
        result = await payment_service.initiate_payment(payment_input)
        
        assert result["success"] is True
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        
        # Vérifier que la description ne contient pas de caractères spéciaux
        cleaned_description = payload["description"]
        assert "'" not in cleaned_description
        assert "(" not in cleaned_description
        assert ")" not in cleaned_description
        assert "–" not in cleaned_description
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_transaction_id_format(
        self,
        mock_client_class,
        payment_service,
        test_training_application,
        test_user,
        mock_cinetpay_response_success
    ):
        """Test que le transaction_id est correctement formaté (sans tirets)"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_cinetpay_response_success
        mock_response.headers = {}
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description="Test Transaction ID Format",
            payment_provider="CINETPAY",
            payment_method="WALLET",
            customer_name=test_user.last_name,
            customer_surname=test_user.first_name,
            customer_email=test_user.email,
            customer_phone_number=test_user.mobile_number
        )
        
        result = await payment_service.initiate_payment(payment_input)
        
        assert result["success"] is True
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        
        # Vérifier que le transaction_id ne contient pas de tirets
        transaction_id = payload["transaction_id"]
        assert "-" not in transaction_id
        assert len(transaction_id) <= 25  # Limite CinetPay


class TestPaymentErrorHandling:
    """Tests de gestion des erreurs"""
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_payment_api_timeout(
        self,
        mock_client_class,
        payment_service,
        test_training_application,
        test_user
    ):
        """Test de gestion d'un timeout de l'API CinetPay"""
        import httpx
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        mock_client_class.return_value = mock_client
        
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description="Test Timeout",
            payment_provider="CINETPAY",
            payment_method="WALLET",
            customer_name=test_user.last_name,
            customer_surname=test_user.first_name,
            customer_email=test_user.email,
            customer_phone_number=test_user.mobile_number
        )
        
        result = await payment_service.initiate_payment(payment_input)
        
        assert result["success"] is False
        assert "timeout" in result.get("message", "").lower() or "TIMEOUT" in result.get("code", "")
    
    @pytest.mark.asyncio
    @patch('src.api.payments.service.httpx.AsyncClient')
    async def test_payment_api_connection_error(
        self,
        mock_client_class,
        payment_service,
        test_training_application,
        test_user
    ):
        """Test de gestion d'une erreur de connexion à l'API CinetPay"""
        import httpx
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        mock_client_class.return_value = mock_client
        
        payment_input = PaymentInitInput(
            payable=test_training_application,
            amount=10000.0,
            product_currency="XOF",
            description="Test Connection Error",
            payment_provider="CINETPAY",
            payment_method="WALLET",
            customer_name=test_user.last_name,
            customer_surname=test_user.first_name,
            customer_email=test_user.email,
            customer_phone_number=test_user.mobile_number
        )
        
        result = await payment_service.initiate_payment(payment_input)
        
        assert result["success"] is False
        assert "connection" in result.get("message", "").lower() or "CONNECTION" in result.get("code", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
