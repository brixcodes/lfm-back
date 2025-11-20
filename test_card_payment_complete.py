"""
Script complet de test pour paiement par Carte Bancaire
Montant: 500 XAF
Carte: 4834 5600 7033 2785 (05/26, CVV: 329)
Continue automatiquement jusqu'à validation complète
"""

import asyncio
import httpx
import json
from datetime import datetime
from src.config import settings
from src.helper.utils import clean_cinetpay_string, clean_payment_description
import uuid
import sys
import math


# Informations de test
CARD_NUMBER = "4834 5600 7033 2785"
CARD_EXPIRY = "05/26"
CARD_CVV = "329"
AMOUNT = 500.0
CURRENCY = "XAF"
CUSTOMER_PHONE = "+237657807309"


def round_up_to_nearest_5(x: float) -> int:
    """Arrondir au multiple de 5 supérieur"""
    return int(math.ceil(x / 5.0)) * 5


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
    except httpx.HTTPError as e:
        print(f"   ⚠️  Erreur HTTP: {str(e)}")
        return None
    except Exception as e:
        print(f"   ⚠️  Erreur: {str(e)}")
        return None


async def initiate_payment():
    """Initialise un paiement par Carte Bancaire avec CinetPay"""
    print("\n" + "="*80)
    print("TEST COMPLET: PAIEMENT CARTE BANCAIRE")
    print("="*80)
    print(f"Montant: {AMOUNT} {CURRENCY}")
    print(f"Carte: {CARD_NUMBER}")
    print(f"Expiration: {CARD_EXPIRY}, CVV: {CARD_CVV}")
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
    description = clean_payment_description("Test paiement Carte Bancaire 500 XAF")
    
    # Préparer le payload selon la documentation CinetPay
    # Pour la carte bancaire, tous les champs client sont OBLIGATOIRES
    payload = {
        "amount": final_amount,
        "currency": CURRENCY,
        "description": description,
        "apikey": settings.CINETPAY_API_KEY,
        "site_id": settings.CINETPAY_SITE_ID,
        "transaction_id": transaction_id,
        "channels": "CREDIT_CARD",  # Canal spécifique pour carte bancaire
        "return_url": settings.CINETPAY_RETURN_URL,
        "notify_url": settings.CINETPAY_NOTIFY_URL,
        "metadata": "Test-Card-Payment-500",
        "invoice_data": {
            "Service": "LAFAOM-MAO",
            "Montant": f"{final_amount} {CURRENCY}",
            "Reference": transaction_id[:20]
        },
        "lang": "fr",
        # Informations client OBLIGATOIRES pour activer la carte bancaire
        "customer_name": clean_cinetpay_string("Test", max_length=100),
        "customer_surname": clean_cinetpay_string("User", max_length=100),
        "customer_email": "test@example.com",
        "customer_phone_number": CUSTOMER_PHONE,
        "customer_address": clean_cinetpay_string("Yaoundé", max_length=200),
        "customer_city": clean_cinetpay_string("Yaoundé", max_length=100),
        "customer_country": "CM",
        "customer_state": "CM",
        "customer_zip_code": "065100"
    }
    
    print("\n[ÉTAPE 1/4] Initialisation du paiement...")
    print("-" * 80)
    print(f"   Transaction ID: {transaction_id}")
    print(f"   Montant: {final_amount} {CURRENCY}")
    print(f"   Canal: CREDIT_CARD")
    print(f"   API Key: {settings.CINETPAY_API_KEY[:20]}...")
    print(f"   Site ID: {settings.CINETPAY_SITE_ID}")
    print(f"\n   ✅ Tous les champs client requis sont présents pour activer la carte bancaire")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "LAFAOM-Backend/1.0"
            }
            
            print(f"\n   📤 Envoi de la requête à CinetPay...")
            response = await client.post(
                "https://api-checkout.cinetpay.com/v2/payment",
                json=payload,
                headers=headers
            )
            
            print(f"   📥 Code de réponse: {response.status_code}")
            
            if response.status_code != 200:
                print(f"\n❌ ERREUR HTTP: {response.status_code}")
                print(f"   Réponse: {response.text[:500]}")
                return None, None
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                print(f"\n❌ ERREUR: Réponse JSON invalide")
                print(f"   Réponse: {response.text[:500]}")
                return None, None
            
            response_code = response_data.get("code")
            response_message = response_data.get("message", "")
            
            print(f"   Code CinetPay: {response_code}")
            print(f"   Message: {response_message}")
            
            if response_code == "201":
                payment_url = response_data["data"]["payment_url"]
                payment_token = response_data["data"].get("payment_token", "")
                api_response_id = response_data.get("api_response_id", "")
                
                print(f"\n✅ Paiement initialisé avec succès!")
                print(f"   Lien de paiement: {payment_url}")
                print(f"   Payment Token: {payment_token[:50]}..." if payment_token else "   Payment Token: N/A")
                print(f"   API Response ID: {api_response_id}")
                
                print(f"\n   💳 INSTRUCTIONS:")
                print(f"   1. Ouvrez ce lien dans votre navigateur: {payment_url}")
                print(f"   2. Complétez le formulaire de carte bancaire:")
                print(f"      - Numéro de carte: {CARD_NUMBER}")
                print(f"      - Date d'expiration: {CARD_EXPIRY}")
                print(f"      - CVV: {CARD_CVV}")
                print(f"   3. Le système vérifiera automatiquement le statut")
                
                return transaction_id, payment_url
            else:
                error_code = response_data.get("code", "UNKNOWN")
                error_message = response_data.get("message", "Unknown error")
                error_description = response_data.get("description", "")
                
                print(f"\n❌ ERREUR lors de l'initialisation:")
                print(f"   Code: {error_code}")
                print(f"   Message: {error_message}")
                if error_description:
                    print(f"   Description: {error_description}")
                
                # Afficher le payload pour debug si nécessaire
                if error_code in ["608", "624"]:
                    print(f"\n   🔍 Payload envoyé:")
                    print(f"   {json.dumps(payload, indent=2, ensure_ascii=False)[:500]}")
                
                return None, None
                
    except httpx.TimeoutException:
        print(f"\n❌ ERREUR: Timeout lors de la connexion à CinetPay")
        return None, None
    except httpx.ConnectError:
        print(f"\n❌ ERREUR: Impossible de se connecter à CinetPay")
        return None, None
    except Exception as e:
        print(f"\n❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


async def monitor_payment_status(transaction_id: str):
    """Surveille le statut d'un paiement jusqu'à validation complète"""
    print("\n[ÉTAPE 2/4] Vérification initiale du statut...")
    print("-" * 80)
    
    # Première vérification immédiate
    status_result = await check_payment_status(transaction_id)
    
    if status_result:
        code = status_result.get("code", "")
        data = status_result.get("data", {})
        status = data.get("status", "")
        
        print(f"   Statut initial: {status} (Code: {code})")
        
        # Si déjà accepté (peu probable mais possible)
        if code == "00" and status == "ACCEPTED":
            print(f"\n✅ Paiement déjà accepté!")
            return True, status_result
    
    print("\n[ÉTAPE 3/4] Surveillance du paiement...")
    print("-" * 80)
    print("   ⏳ En attente de validation du paiement...")
    print("   💡 Le système vérifie automatiquement toutes les 5 secondes")
    print("   💡 Complétez le formulaire de carte bancaire maintenant\n")
    
    max_attempts = 120  # Maximum 120 tentatives (10 minutes)
    attempt = 0
    last_status = None
    status_count = {}
    last_print_time = datetime.now()
    
    while attempt < max_attempts:
        attempt += 1
        
        try:
            # Afficher le numéro de tentative toutes les 10 tentatives
            if attempt % 10 == 0:
                elapsed = (datetime.now() - last_print_time).total_seconds()
                print(f"   ⏱️  Tentative {attempt}/{max_attempts} (~{int(elapsed)}s écoulées)...")
            
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
                last_print_time = datetime.now()
            
            # Vérifier si le paiement est accepté
            if code == "00" and status == "ACCEPTED":
                print("\n\n" + "="*80)
                print("✅ PAIEMENT ACCEPTÉ AVEC SUCCÈS!")
                print("="*80)
                return True, status_result
            
            # Vérifier si le paiement est refusé
            elif status in ["REFUSED", "CANCELLED"]:
                print(f"\n\n❌ PAIEMENT REFUSÉ OU ANNULÉ")
                print(f"   Statut: {status}")
                print(f"   Code: {code}")
                print(f"   Message: {message}")
                return False, status_result
            
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
    print(f"   Dernier statut: {last_status}")
    print(f"   Résumé des statuts: {status_count}")
    return False, None


async def display_final_results(transaction_id: str, status_result: dict):
    """Affiche les résultats finaux du paiement"""
    print("\n[ÉTAPE 4/4] Résultats finaux...")
    print("-" * 80)
    
    if status_result:
        code = status_result.get("code", "")
        message = status_result.get("message", "")
        data = status_result.get("data", {})
        status = data.get("status", "")
        
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Code: {code}")
        print(f"   Message: {message}")
        print(f"   Statut: {status}")
        
        if data:
            print(f"\n   Détails de la transaction:")
            print(f"   - Méthode de paiement: {data.get('payment_method', 'N/A')}")
            print(f"   - Montant: {data.get('amount', 0)} {data.get('currency', '')}")
            print(f"   - Date de paiement: {data.get('payment_date', 'N/A')}")
            print(f"   - Description: {data.get('description', 'N/A')}")
            print(f"   - Operator ID: {data.get('operator_id', 'N/A')}")
            
            if data.get('fund_availability_date'):
                print(f"   - Date de disponibilité des fonds: {data.get('fund_availability_date', 'N/A')}")
            
            if data.get('metadata'):
                print(f"   - Métadonnées: {data.get('metadata', 'N/A')}")
        
        api_response_id = status_result.get("api_response_id", "")
        if api_response_id:
            print(f"\n   API Response ID: {api_response_id}")


async def main():
    """Fonction principale"""
    print("\n" + "="*80)
    print("TEST COMPLET: PAIEMENT CARTE BANCAIRE - 500 XAF")
    print("="*80)
    print("\nCe script va:")
    print("1. ✅ Initialiser un paiement de 500 XAF par carte bancaire")
    print("2. ✅ Générer un lien de paiement CinetPay")
    print("3. ✅ Vérifier automatiquement le statut toutes les 5 secondes")
    print("4. ✅ Continuer jusqu'à ce que le paiement soit accepté")
    print("\n💳 Informations de carte:")
    print(f"   - Numéro: {CARD_NUMBER}")
    print(f"   - Expiration: {CARD_EXPIRY}")
    print(f"   - CVV: {CARD_CVV}")
    print("\n⚠️  Assurez-vous de compléter le formulaire de carte bancaire!")
    print("="*80)
    
    print("\n🚀 Démarrage automatique du test...\n")
    
    # Étape 1: Initialiser le paiement
    transaction_id, payment_url = await initiate_payment()
    
    if transaction_id is None:
        print("\n❌ Impossible d'initialiser le paiement.")
        print("   Vérifiez:")
        print("   - Que vos credentials CinetPay sont dans le fichier .env")
        print("   - Que l'API CinetPay est accessible")
        print("   - Les erreurs ci-dessus pour plus de détails\n")
        sys.exit(1)
    
    # Étape 2-3: Surveiller le paiement
    success, status_result = await monitor_payment_status(transaction_id)
    
    # Étape 4: Afficher les résultats
    await display_final_results(transaction_id, status_result)
    
    # Résultat final
    print("\n" + "="*80)
    if success:
        print("✅ TEST RÉUSSI: Le paiement a été validé avec succès!")
        print("="*80 + "\n")
        sys.exit(0)
    else:
        print("⚠️  TEST INCOMPLET: Le paiement n'a pas été validé")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Vous pouvez vérifier le statut plus tard avec:")
        print(f"   python test_payment_simulation.py (option 3)")
        print("="*80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur (Ctrl+C)")
        print("   Le paiement peut toujours être en cours de traitement")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

