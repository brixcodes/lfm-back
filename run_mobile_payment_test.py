"""
Script pour lancer automatiquement un test de paiement Mobile Money
Montant: 1000 XAF
Numéro: +237657807309
Continue jusqu'à ce que le paiement soit accepté
"""

import asyncio
import httpx
import json
from datetime import datetime
from src.api.payments.service import PaymentService, CinetPayService
from src.api.payments.schemas import PaymentInitInput
from src.database import get_session_async
import uuid
import sys


# Informations de test
MOBILE_PHONE = "+237657807309"
AMOUNT = 1000.0
CURRENCY = "XAF"


class MockPayable:
    """Mock d'un objet payable pour les tests"""
    def __init__(self, id: str, class_name: str = "StudentApplication"):
        self.id = id
        self.__class__.__name__ = class_name


async def run_mobile_payment_test():
    """Lance un test de paiement Mobile Money et continue jusqu'à validation"""
    print("\n" + "="*80)
    print("TEST AUTOMATIQUE: PAIEMENT MOBILE MONEY")
    print("="*80)
    print(f"Numéro de téléphone: {MOBILE_PHONE}")
    print(f"Montant: {AMOUNT} {CURRENCY}")
    print("="*80)
    
    # Créer un objet payable mock
    payable = MockPayable(str(uuid.uuid4()), "StudentApplication")
    
    # Créer les données de paiement
    payment_data = PaymentInitInput(
        payable=payable,
        amount=AMOUNT,
        product_currency=CURRENCY,
        description="Test paiement Mobile Money 1000 XAF",
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
        
        print("\n[ÉTAPE 1/3] Initialisation du paiement...")
        print("-" * 80)
        
        try:
            result = await payment_service.initiate_payment(payment_data)
            
            if not result.get("success"):
                print(f"❌ ERREUR lors de l'initialisation:")
                print(f"   Message: {result.get('message', 'Unknown error')}")
                print(f"   Code: {result.get('code', 'N/A')}")
                return False
            
            transaction_id = result.get("transaction_id")
            payment_link = result.get("payment_link")
            
            print(f"✅ Paiement initialisé avec succès!")
            print(f"   Transaction ID: {transaction_id}")
            print(f"   Lien de paiement: {payment_link}")
            print(f"\n   📱 Ouvrez ce lien dans votre navigateur pour valider le paiement")
            print(f"   📱 Ou validez directement sur votre téléphone: {MOBILE_PHONE}")
            
            # Étape 2: Vérification du statut en boucle
            print("\n[ÉTAPE 2/3] Vérification du statut du paiement...")
            print("-" * 80)
            print("   ⏳ En attente de validation du paiement...")
            print("   💡 Le système vérifie automatiquement toutes les 5 secondes")
            print("   💡 Validez le paiement sur votre téléphone maintenant\n")
            
            max_attempts = 60  # Maximum 60 tentatives (5 minutes)
            attempt = 0
            last_status = None
            
            while attempt < max_attempts:
                attempt += 1
                
                try:
                    print(f"   Tentative {attempt}/{max_attempts}...", end=" ", flush=True)
                    
                    status_result = await CinetPayService.check_cinetpay_payment_status(transaction_id)
                    
                    code = status_result.get("code", "")
                    message = status_result.get("message", "")
                    data = status_result.get("data", {})
                    status = data.get("status", "")
                    
                    # Afficher le statut seulement s'il a changé
                    if status != last_status:
                        print(f"\n   📊 Statut: {status} (Code: {code})")
                        last_status = status
                    else:
                        print(".", end="", flush=True)
                    
                    # Vérifier si le paiement est accepté
                    if code == "00" and status == "ACCEPTED":
                        print("\n\n" + "="*80)
                        print("✅ PAIEMENT ACCEPTÉ AVEC SUCCÈS!")
                        print("="*80)
                        
                        print(f"\n[ÉTAPE 3/3] Détails de la transaction:")
                        print("-" * 80)
                        print(f"   Transaction ID: {transaction_id}")
                        print(f"   Statut: {status}")
                        print(f"   Méthode de paiement: {data.get('payment_method', 'N/A')}")
                        print(f"   Montant: {data.get('amount', 0)} {data.get('currency', '')}")
                        print(f"   Date de paiement: {data.get('payment_date', 'N/A')}")
                        print(f"   Description: {data.get('description', 'N/A')}")
                        print(f"   Operator ID: {data.get('operator_id', 'N/A')}")
                        
                        if data.get('fund_availability_date'):
                            print(f"   Date de disponibilité des fonds: {data.get('fund_availability_date', 'N/A')}")
                        
                        print("\n" + "="*80)
                        print("✅ TEST RÉUSSI: Le paiement a été validé avec succès!")
                        print("="*80 + "\n")
                        return True
                    
                    # Vérifier si le paiement est refusé
                    elif status in ["REFUSED", "CANCELLED"]:
                        print(f"\n\n❌ PAIEMENT REFUSÉ OU ANNULÉ")
                        print(f"   Statut: {status}")
                        print(f"   Code: {code}")
                        print(f"   Message: {message}")
                        return False
                    
                    # Si toujours en attente, continuer
                    elif status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", 
                                   "WAITING_CUSTOMER_PAYMENT", "WAITING_CUSTOMER_OTP_CODE", "PENDING"]:
                        # Attendre 5 secondes avant la prochaine vérification
                        await asyncio.sleep(5)
                        continue
                    
                    else:
                        # Statut inconnu, continuer quand même
                        print(f"\n   ⚠️  Statut inconnu: {status}, continuation...")
                        await asyncio.sleep(5)
                        continue
                        
                except Exception as e:
                    print(f"\n   ⚠️  Erreur lors de la vérification: {str(e)}")
                    print(f"   Nouvelle tentative dans 5 secondes...")
                    await asyncio.sleep(5)
                    continue
            
            # Si on arrive ici, on a dépassé le nombre maximum de tentatives
            print(f"\n\n⏱️  TIMEOUT: Le paiement n'a pas été validé dans les temps")
            print(f"   Nombre de tentatives: {max_attempts}")
            print(f"   Transaction ID: {transaction_id}")
            print(f"   Dernier statut: {last_status}")
            print(f"\n   💡 Vous pouvez vérifier le statut plus tard avec:")
            print(f"   python test_payment_simulation.py (option 3)")
            return False
                
        except Exception as e:
            print(f"\n❌ ERREUR: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        break
    
    return False


async def main():
    """Fonction principale"""
    print("\n" + "="*80)
    print("SIMULATION AUTOMATIQUE DE PAIEMENT MOBILE MONEY")
    print("="*80)
    print("\nCe script va:")
    print("1. Initialiser un paiement de 1000 XAF")
    print("2. Générer un lien de paiement")
    print("3. Vérifier automatiquement le statut toutes les 5 secondes")
    print("4. Continuer jusqu'à ce que le paiement soit accepté")
    print("\n⚠️  Assurez-vous d'avoir validé le paiement sur votre téléphone!")
    print("="*80)
    
    print("\n🚀 Démarrage automatique du test...\n")
    
    success = await run_mobile_payment_test()
    
    if success:
        print("\n🎉 Félicitations! Le test est terminé avec succès.\n")
        sys.exit(0)
    else:
        print("\n⚠️  Le test n'a pas abouti. Vérifiez les erreurs ci-dessus.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

