"""
Script de test pour simuler un paiement complet jusqu'à la validation
Teste Mobile Money et Carte Bancaire avec les informations fournies
"""

import asyncio
import httpx
import json
from datetime import datetime
from src.api.payments.service import PaymentService, CinetPayService
from src.api.payments.schemas import PaymentInitInput, CinetPayInit
from src.api.training.models import StudentApplication, TrainingSession, Training
from src.database import get_session_async
from sqlalchemy.ext.asyncio import AsyncSession
import uuid


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


async def test_mobile_money_payment():
    """Test complet d'un paiement Mobile Money"""
    print("\n" + "="*80)
    print("TEST 1: PAIEMENT MOBILE MONEY")
    print("="*80)
    print(f"Numéro de téléphone: {MOBILE_PHONE}")
    print(f"Montant: 10000 XAF")
    print("-"*80)
    
    # Créer un objet payable mock
    payable = MockPayable(str(uuid.uuid4()), "StudentApplication")
    
    # Créer les données de paiement
    payment_data = PaymentInitInput(
        payable=payable,
        amount=10000.0,
        product_currency="XAF",
        description="Test paiement Mobile Money",
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
    
    # Initialiser le service
    async for session in get_session_async():
        payment_service = PaymentService(session=session)
        
        print("\n[1/3] Initialisation du paiement...")
        try:
            result = await payment_service.initiate_payment(payment_data)
            
            if result.get("success"):
                transaction_id = result.get("transaction_id")
                payment_link = result.get("payment_link")
                
                print(f"✅ Paiement initialisé avec succès!")
                print(f"   Transaction ID: {transaction_id}")
                print(f"   Lien de paiement: {payment_link}")
                
                print("\n[2/3] Simulation de la validation du paiement...")
                print("   → L'utilisateur doit valider le paiement sur son téléphone")
                print(f"   → Numéro: {MOBILE_PHONE}")
                print("   → En attente de validation...")
                
                # Simuler la vérification du statut
                await asyncio.sleep(2)  # Simuler un délai
                
                print("\n[3/3] Vérification du statut du paiement...")
                try:
                    status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
                    
                    status = status_result.get("data", {}).get("status", "")
                    code = status_result.get("code", "")
                    
                    if code == "00" and status == "ACCEPTED":
                        print(f"✅ Paiement accepté!")
                        print(f"   Statut: {status}")
                        print(f"   Méthode: {status_result.get('data', {}).get('payment_method', 'N/A')}")
                        print(f"   Montant reçu: {status_result.get('data', {}).get('amount', 0)} {status_result.get('data', {}).get('currency', '')}")
                    elif status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", "PENDING"]:
                        print(f"⏳ Paiement en attente de validation")
                        print(f"   Statut: {status}")
                        print(f"   Le paiement est en cours, veuillez valider sur votre téléphone")
                    else:
                        print(f"❌ Paiement refusé ou annulé")
                        print(f"   Statut: {status}")
                        print(f"   Code: {code}")
                        
                except Exception as e:
                    print(f"⚠️  Erreur lors de la vérification: {str(e)}")
                    print("   Le paiement peut être en cours de traitement")
                
            else:
                print(f"❌ Erreur lors de l'initialisation: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
        
        break


async def test_credit_card_payment():
    """Test complet d'un paiement par carte bancaire"""
    print("\n" + "="*80)
    print("TEST 2: PAIEMENT CARTE BANCAIRE")
    print("="*80)
    print(f"Numéro de carte: {CARD_NUMBER}")
    print(f"Date d'expiration: {CARD_EXPIRY}")
    print(f"CVV: {CARD_CVV}")
    print(f"Montant: 10000 XAF")
    print("-"*80)
    
    # Créer un objet payable mock
    payable = MockPayable(str(uuid.uuid4()), "StudentApplication")
    
    # Créer les données de paiement
    payment_data = PaymentInitInput(
        payable=payable,
        amount=10000.0,
        product_currency="XAF",
        description="Test paiement Carte Bancaire",
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
    
    # Initialiser le service
    async for session in get_session_async():
        payment_service = PaymentService(session=session)
        
        print("\n[1/3] Initialisation du paiement...")
        try:
            result = await payment_service.initiate_payment(payment_data)
            
            if result.get("success"):
                transaction_id = result.get("transaction_id")
                payment_link = result.get("payment_link")
                
                print(f"✅ Paiement initialisé avec succès!")
                print(f"   Transaction ID: {transaction_id}")
                print(f"   Lien de paiement: {payment_link}")
                
                print("\n[2/3] Simulation de la validation du paiement...")
                print("   → L'utilisateur doit compléter le formulaire de carte bancaire")
                print(f"   → Numéro de carte: {CARD_NUMBER}")
                print(f"   → Date d'expiration: {CARD_EXPIRY}")
                print(f"   → CVV: {CARD_CVV}")
                print("   → En attente de validation...")
                
                # Simuler la vérification du statut
                await asyncio.sleep(2)  # Simuler un délai
                
                print("\n[3/3] Vérification du statut du paiement...")
                try:
                    status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
                    
                    status = status_result.get("data", {}).get("status", "")
                    code = status_result.get("code", "")
                    
                    if code == "00" and status == "ACCEPTED":
                        print(f"✅ Paiement accepté!")
                        print(f"   Statut: {status}")
                        print(f"   Méthode: {status_result.get('data', {}).get('payment_method', 'N/A')}")
                        print(f"   Montant reçu: {status_result.get('data', {}).get('amount', 0)} {status_result.get('data', {}).get('currency', '')}")
                    elif status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", "PENDING"]:
                        print(f"⏳ Paiement en attente de validation")
                        print(f"   Statut: {status}")
                        print(f"   Le paiement est en cours, veuillez compléter le formulaire")
                    else:
                        print(f"❌ Paiement refusé ou annulé")
                        print(f"   Statut: {status}")
                        print(f"   Code: {code}")
                        print(f"   Message: {status_result.get('message', 'N/A')}")
                        
                except Exception as e:
                    print(f"⚠️  Erreur lors de la vérification: {str(e)}")
                    print("   Le paiement peut être en cours de traitement")
                
            else:
                print(f"❌ Erreur lors de l'initialisation: {result.get('message', 'Unknown error')}")
                print(f"   Code: {result.get('code', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            import traceback
            traceback.print_exc()
        
        break


async def test_payment_status_check(transaction_id: str):
    """Vérifier le statut d'une transaction existante"""
    print("\n" + "="*80)
    print("VÉRIFICATION DU STATUT D'UNE TRANSACTION")
    print("="*80)
    print(f"Transaction ID: {transaction_id}")
    print("-"*80)
    
    try:
        status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
        
        code = status_result.get("code", "")
        message = status_result.get("message", "")
        data = status_result.get("data", {})
        
        print(f"\nCode: {code}")
        print(f"Message: {message}")
        
        if data:
            print(f"\nDétails de la transaction:")
            print(f"  - Statut: {data.get('status', 'N/A')}")
            print(f"  - Montant: {data.get('amount', 0)} {data.get('currency', '')}")
            print(f"  - Méthode de paiement: {data.get('payment_method', 'N/A')}")
            print(f"  - Date de paiement: {data.get('payment_date', 'N/A')}")
            print(f"  - Description: {data.get('description', 'N/A')}")
            
            if code == "00" and data.get('status') == "ACCEPTED":
                print("\n✅ Transaction acceptée avec succès!")
            elif data.get('status') in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", "PENDING"]:
                print("\n⏳ Transaction en attente de validation")
            else:
                print("\n❌ Transaction refusée ou annulée")
        else:
            print("\n⚠️  Aucune donnée disponible")
            
    except Exception as e:
        print(f"\n❌ Erreur lors de la vérification: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Fonction principale pour exécuter les tests"""
    print("\n" + "="*80)
    print("TESTS DE SIMULATION DE PAIEMENT CINETPAY")
    print("="*80)
    print("\nCe script simule le processus complet de paiement jusqu'à la validation")
    print("Il teste les deux méthodes de paiement: Mobile Money et Carte Bancaire")
    print("\n⚠️  NOTE: Ces tests utilisent l'API réelle de CinetPay")
    print("    Assurez-vous que vos credentials sont correctement configurés dans .env")
    print("="*80)
    
    # Demander à l'utilisateur quel test exécuter
    print("\nChoisissez un test à exécuter:")
    print("1. Test Mobile Money (numéro: +237657807309)")
    print("2. Test Carte Bancaire (carte: 4834 5600 7033 2785)")
    print("3. Vérifier le statut d'une transaction existante")
    print("4. Exécuter tous les tests")
    print("0. Quitter")
    
    choice = input("\nVotre choix (0-4): ").strip()
    
    if choice == "1":
        await test_mobile_money_payment()
    elif choice == "2":
        await test_credit_card_payment()
    elif choice == "3":
        transaction_id = input("Entrez le Transaction ID: ").strip()
        if transaction_id:
            await test_payment_status_check(transaction_id)
        else:
            print("❌ Transaction ID requis")
    elif choice == "4":
        await test_mobile_money_payment()
        await asyncio.sleep(2)
        await test_credit_card_payment()
    elif choice == "0":
        print("Au revoir!")
        return
    else:
        print("❌ Choix invalide")
    
    print("\n" + "="*80)
    print("Tests terminés")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

