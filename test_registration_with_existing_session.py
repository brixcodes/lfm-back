#!/usr/bin/env python3
"""
Script pour tester l'inscription avec la session existante
"""

import asyncio
import httpx
import json

async def test_registration_with_existing_session():
    """Test de l'inscription avec la session existante"""
    
    base_url = "https://api.lafaom-mao.org/api/v1"
    
    # Utiliser la session existante que nous avons trouvée
    session_id = "cb425364-1856-44a0-838e-ea8f6d62aab1"
    
    # Données de test pour l'inscription
    registration_data = {
        "email": "test@example.com",
        "target_session_id": session_id,
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "+221123456789",
        "country_code": "SN",
        "civility": "M",
        "city": "Dakar",
        "address": "123 Rue de la Paix",
        "date_of_birth": "1990-01-01",
        "payment_method": "ONLINE",
        "attachments": []
    }
    
    print("🧪 Test d'inscription à une formation")
    print(f"🌐 URL: {base_url}")
    print(f"📧 Email: {registration_data['email']}")
    print(f"👤 Nom: {registration_data['first_name']} {registration_data['last_name']}")
    print(f"📱 Téléphone: {registration_data['phone_number']}")
    print(f"🌍 Pays: {registration_data['country_code']}")
    print(f"💳 Méthode de paiement: {registration_data['payment_method']}")
    print(f"🎯 Session ID: {session_id}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
            print("🚀 Envoi de la requête d'inscription...")
            response = await client.post(
                f"{base_url}/student-applications",
                json=registration_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📋 Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                response_data = response.json()
                print("\n✅ Inscription réussie!")
                print(f"📝 Message: {response_data.get('message', 'N/A')}")
                
                # Vérifier la structure de la réponse
                data = response_data.get('data', {})
                print(f"\n📦 Structure de la réponse:")
                print(f"  - Clés disponibles: {list(data.keys())}")
                
                # Vérifier les informations de la candidature
                student_app = data.get('student_application')
                if student_app:
                    print(f"\n📋 Informations de la candidature:")
                    print(f"  - ID: {student_app.get('id')}")
                    print(f"  - Numéro: {student_app.get('application_number')}")
                    print(f"  - Statut: {student_app.get('status')}")
                    print(f"  - Frais d'inscription: {student_app.get('registration_fee')}")
                    print(f"  - Frais de formation: {student_app.get('training_fee')}")
                    print(f"  - Devise: {student_app.get('currency')}")
                
                # Vérifier les informations de paiement
                payment = data.get('payment')
                if payment:
                    print(f"\n💳 Informations de paiement:")
                    print(f"  - Provider: {payment.get('payment_provider')}")
                    print(f"  - Montant: {payment.get('amount')}")
                    print(f"  - Devise: {payment.get('currency')}")
                    print(f"  - Transaction ID: {payment.get('transaction_id')}")
                    print(f"  - Lien de paiement: {payment.get('payment_link')}")
                    print(f"  - URL de notification: {payment.get('notify_url')}")
                    print(f"  - Message: {payment.get('message')}")
                    
                    # Vérifier si le lien de paiement est présent
                    if payment.get('payment_link'):
                        print(f"\n🎉 SUCCÈS: Les informations de paiement sont correctement retournées!")
                        print(f"🔗 Lien de paiement: {payment['payment_link']}")
                        print(f"\n✅ PROBLÈME RÉSOLU: L'inscription à une formation retourne maintenant les informations de paiement!")
                        return True
                    else:
                        print(f"\n❌ PROBLÈME: Le lien de paiement est manquant!")
                        return False
                else:
                    print(f"\n❌ PROBLÈME: Aucune information de paiement retournée!")
                    return False
                
                # Afficher la réponse complète pour debug
                print(f"\n🔍 Réponse complète:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
                
            else:
                print(f"\n❌ Erreur lors de l'inscription:")
                print(f"Status: {response.status_code}")
                print(f"Réponse: {response.text}")
                return False
                
    except httpx.ConnectError as e:
        print(f"❌ Impossible de se connecter au serveur: {e}")
        return False
    except httpx.HTTPStatusError as e:
        print(f"❌ Erreur HTTP: {e.response.status_code}")
        print(f"Réponse: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Test d'inscription avec session existante")
    print("=" * 60)
    
    success = asyncio.run(test_registration_with_existing_session())
    
    if success:
        print(f"\n🎉 TEST RÉUSSI!")
        print(f"✅ Les informations de paiement sont correctement retournées lors de l'inscription à une formation.")
        print(f"✅ Le problème de finalisation du paiement a été résolu!")
    else:
        print(f"\n❌ TEST ÉCHOUÉ!")
        print(f"❌ Problème persistant avec le retour des informations de paiement.")
