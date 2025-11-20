"""
Script simplifié pour tester un paiement Mobile Money
Montant: 1000 XAF
Numéro: +237657807309
Utilise directement l'API CinetPay sans passer par la base de données
"""

import asyncio
import httpx
import json
from datetime import datetime
from src.config import settings
from src.api.payments.service import CinetPayService
from src.api.payments.schemas import CinetPayInit
from src.helper.utils import clean_cinetpay_string, clean_payment_description
import uuid
import sys
import math


# Informations de test
MOBILE_PHONE = "+237657807309"
AMOUNT = 1000.0
CURRENCY = "XAF"


def round_up_to_nearest_5(x: float) -> int:
    """Arrondir au multiple de 5 supérieur"""
    return int(math.ceil(x / 5.0)) * 5


async def initiate_payment_direct():
    """Initialise directement un paiement avec CinetPay"""
    print("\n" + "="*80)
    print("TEST AUTOMATIQUE: PAIEMENT MOBILE MONEY")
    print("="*80)
    print(f"Numéro de téléphone: {MOBILE_PHONE}")
    print(f"Montant: {AMOUNT} {CURRENCY}")
    print("="*80)
    
    # Vérifier les credentials
    if not settings.CINETPAY_API_KEY or settings.CINETPAY_API_KEY.strip() == "":
        print("❌ ERREUR: CINETPAY_API_KEY n'est pas configuré dans .env")
        return None, None
    
    if not settings.CINETPAY_SITE_ID or settings.CINETPAY_SITE_ID.strip() == "":
        print("❌ ERREUR: CINETPAY_SITE_ID n'est pas configuré dans .env")
        return None, None
    
    # Générer un transaction_id
    transaction_id = str(uuid.uuid4()).replace('-', '')[:25]
    
    # Arrondir le montant au multiple de 5
    final_amount = round_up_to_nearest_5(AMOUNT)
    
    # Nettoyer la description
    description = clean_payment_description("Test paiement Mobile Money 1000 XAF")
    
    # Préparer le payload
    payload = {
        "amount": final_amount,
        "currency": CURRENCY,
        "description": description,
        "apikey": settings.CINETPAY_API_KEY,
        "site_id": settings.CINETPAY_SITE_ID,
        "transaction_id": transaction_id,
        "channels": "MOBILE_MONEY",
        "return_url": settings.CINETPAY_RETURN_URL,
        "notify_url": settings.CINETPAY_NOTIFY_URL,
        "meta": "Test-Mobile-Money-1000",
        "invoice_data": {
            "Service": "LAFAOM-MAO",
            "Montant": f"{final_amount} {CURRENCY}",
            "Reference": transaction_id[:20]
        },
        "lang": "fr",
        "customer_name": clean_cinetpay_string("Test", max_length=100),
        "customer_surname": clean_cinetpay_string("User", max_length=100),
        "customer_email": "test@example.com",
        "customer_phone_number": MOBILE_PHONE,
        "customer_address": clean_cinetpay_string("Yaoundé", max_length=200),
        "customer_city": clean_cinetpay_string("Yaoundé", max_length=100),
        "customer_country": "CM",
        "customer_state": "CM",
        "customer_zip_code": "065100"
    }
    
    print("\n[ÉTAPE 1/3] Initialisation du paiement...")
    print("-" * 80)
    print(f"   Transaction ID: {transaction_id}")
    print(f"   Montant: {final_amount} {CURRENCY}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "LAFAOM-Backend/1.0"
            }
            
            print(f"   Envoi de la requête à CinetPay...")
            response = await client.post(
                "https://api-checkout.cinetpay.com/v2/payment",
                json=payload,
                headers=headers
            )
            
            print(f"   Code de réponse: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ ERREUR HTTP: {response.status_code}")
                print(f"   Réponse: {response.text}")
                return None, None
            
            response_data = response.json()
            response_code = response_data.get("code")
            
            if response_code == "201":
                payment_url = response_data["data"]["payment_url"]
                payment_token = response_data["data"].get("payment_token", "")
                
                print(f"✅ Paiement initialisé avec succès!")
                print(f"   Lien de paiement: {payment_url}")
                print(f"\n   📱 Ouvrez ce lien dans votre navigateur pour valider le paiement")
                print(f"   📱 Ou validez directement sur votre téléphone: {MOBILE_PHONE}")
                
                return transaction_id, payment_url
            else:
                error_code = response_data.get("code", "UNKNOWN")
                error_message = response_data.get("message", "Unknown error")
                error_description = response_data.get("description", "")
                
                print(f"❌ ERREUR lors de l'initialisation:")
                print(f"   Code: {error_code}")
                print(f"   Message: {error_message}")
                print(f"   Description: {error_description}")
                return None, None
                
    except Exception as e:
        print(f"❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


async def check_payment_status(transaction_id: str):
    """Vérifie le statut d'un paiement"""
    payload = {
        "apikey": settings.CINETPAY_API_KEY,
        "site_id": settings.CINETPAY_SITE_ID,
        "transaction_id": transaction_id
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api-checkout.cinetpay.com/v2/payment/check",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "LAFAOM-Backend/1.0"
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"   ⚠️  Erreur lors de la vérification: {str(e)}")
        return None


async def monitor_payment(transaction_id: str):
    """Surveille le statut d'un paiement jusqu'à validation"""
    print("\n[ÉTAPE 2/3] Vérification du statut du paiement...")
    print("-" * 80)
    print("   ⏳ En attente de validation du paiement...")
    print("   💡 Le système vérifie automatiquement toutes les 5 secondes")
    print("   💡 Validez le paiement sur votre téléphone maintenant\n")
    
    max_attempts = 120  # Maximum 120 tentatives (10 minutes)
    attempt = 0
    last_status = None
    status_count = {}
    
    while attempt < max_attempts:
        attempt += 1
        
        try:
            # Afficher le numéro de tentative toutes les 10 tentatives
            if attempt % 10 == 0:
                print(f"   ⏱️  Tentative {attempt}/{max_attempts}...")
            
            status_result = await check_payment_status(transaction_id)
            
            if status_result is None:
                if attempt % 5 == 0:
                    print(f"   ⚠️  Erreur de connexion, nouvelle tentative...")
                await asyncio.sleep(5)
                continue
            
            code = status_result.get("code", "")
            message = status_result.get("message", "")
            data = status_result.get("data", {})
            status = data.get("status", "")
            
            # Compter les statuts
            status_count[status] = status_count.get(status, 0) + 1
            
            # Afficher le statut seulement s'il a changé ou toutes les 5 tentatives
            if status != last_status or attempt % 5 == 0:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"   [{timestamp}] Statut: {status} (Code: {code}) - Tentative {attempt}")
                last_status = status
            
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
                
                print(f"\n   Nombre de tentatives: {attempt}")
                print(f"   Temps écoulé: ~{attempt * 5} secondes")
                
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
                print(f"   Transaction ID: {transaction_id}")
                return False
            
            # Si toujours en attente, continuer
            elif status in ["WAITING_FOR_CUSTOMER", "WAITING_CUSTOMER_TO_VALIDATE", 
                           "WAITING_CUSTOMER_PAYMENT", "WAITING_CUSTOMER_OTP_CODE", "PENDING"]:
                await asyncio.sleep(5)
                continue
            
            else:
                # Statut inconnu, continuer quand même
                if attempt % 5 == 0:
                    print(f"   ⚠️  Statut inconnu: {status}, continuation...")
                await asyncio.sleep(5)
                continue
                
        except Exception as e:
            if attempt % 5 == 0:
                print(f"   ⚠️  Erreur: {str(e)}")
            await asyncio.sleep(5)
            continue
    
    # Timeout
    print(f"\n\n⏱️  TIMEOUT: Le paiement n'a pas été validé dans les temps")
    print(f"   Nombre de tentatives: {max_attempts}")
    print(f"   Transaction ID: {transaction_id}")
    print(f"   Dernier statut: {last_status}")
    print(f"   Résumé des statuts: {status_count}")
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
    
    # Initialiser le paiement
    transaction_id, payment_url = await initiate_payment_direct()
    
    if transaction_id is None:
        print("\n❌ Impossible d'initialiser le paiement. Vérifiez les erreurs ci-dessus.\n")
        sys.exit(1)
    
    # Surveiller le paiement
    success = await monitor_payment(transaction_id)
    
    if success:
        print("\n🎉 Félicitations! Le test est terminé avec succès.\n")
        sys.exit(0)
    else:
        print("\n⚠️  Le test n'a pas abouti.")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Vous pouvez vérifier le statut plus tard.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

