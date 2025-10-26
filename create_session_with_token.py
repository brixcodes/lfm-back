#!/usr/bin/env python3
"""
Script pour créer une session de formation avec un token d'authentification
"""

import asyncio
import httpx
from datetime import date, timedelta

async def create_training_session_with_token():
    """Créer une session de formation avec le token fourni"""
    
    base_url = "https://api.lafaom-mao.org/api/v1"
    training_id = "01d6b0c8-23db-4382-8cea-74ef48457b45"
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhOWQ0OWM5ZC0xOTRiLTQ2MzgtOWE3OC0zNTZmNDFiMGRlNzQiLCJleHAiOjE3NjE2ODU4Mzl9.fN_GmhzTAFYyGNUQs7Dy25zx1fgQAMK16OjMvwHQWnU"
    
    print("🔧 Création d'une session de formation avec token")
    print(f"🌐 URL: {base_url}")
    print(f"📚 Training ID: {training_id}")
    print(f"🔑 Token: {token[:20]}...")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
            # Headers avec le token d'authentification
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Données pour la session de formation
            today = date.today()
            session_data = {
                "training_id": training_id,
                "start_date": (today + timedelta(days=30)).isoformat(),
                "end_date": (today + timedelta(days=90)).isoformat(),
                "registration_deadline": (today + timedelta(days=15)).isoformat(),
                "available_slots": 50,
                "status": "OPEN_FOR_REGISTRATION",
                "registration_fee": 50.0,
                "training_fee": 500.0,
                "currency": "EUR",
                "required_attachments": []
            }
            
            print("🔧 Données de la session:")
            print(f"📅 Date de début: {session_data['start_date']}")
            print(f"📅 Date de fin: {session_data['end_date']}")
            print(f"📅 Date limite d'inscription: {session_data['registration_deadline']}")
            print(f"👥 Places disponibles: {session_data['available_slots']}")
            print(f"💰 Frais d'inscription: {session_data['registration_fee']} {session_data['currency']}")
            print(f"💰 Frais de formation: {session_data['training_fee']} {session_data['currency']}")
            print(f"📊 Statut: {session_data['status']}")
            
            print("\n🚀 Envoi de la requête de création de session...")
            response = await client.post(
                f"{base_url}/training-sessions",
                json=session_data,
                headers=headers
            )
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📋 Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                response_data = response.json()
                print("\n✅ Session de formation créée avec succès!")
                print(f"📝 Message: {response_data.get('message', 'N/A')}")
                
                # Afficher les détails de la session créée
                session = response_data.get('data', {})
                if session:
                    print(f"\n📚 Détails de la session créée:")
                    print(f"  - ID: {session.get('id')}")
                    print(f"  - Training ID: {session.get('training_id')}")
                    print(f"  - Date de début: {session.get('start_date')}")
                    print(f"  - Date de fin: {session.get('end_date')}")
                    print(f"  - Date limite d'inscription: {session.get('registration_deadline')}")
                    print(f"  - Places disponibles: {session.get('available_slots')}")
                    print(f"  - Statut: {session.get('status')}")
                    print(f"  - Frais d'inscription: {session.get('registration_fee')} {session.get('currency')}")
                    print(f"  - Frais de formation: {session.get('training_fee')} {session.get('currency')}")
                    
                    print(f"\n🎯 ID de session à utiliser pour les tests: {session.get('id')}")
                    return session.get('id')
                else:
                    print("❌ Aucune donnée de session retournée")
                    return None
            else:
                print(f"\n❌ Erreur lors de la création de la session:")
                print(f"Status: {response.status_code}")
                print(f"Réponse: {response.text}")
                return None
                
    except httpx.ConnectError as e:
        print(f"❌ Impossible de se connecter au serveur: {e}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"❌ Erreur HTTP: {e.response.status_code}")
        print(f"Réponse: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Création d'une session de formation avec token")
    print("=" * 60)
    
    session_id = asyncio.run(create_training_session_with_token())
    
    if session_id:
        print(f"\n🎉 Session créée avec succès!")
        print(f"📝 ID de session: {session_id}")
        print(f"\n💡 Vous pouvez maintenant utiliser cet ID pour tester l'inscription:")
        print(f"   target_session_id: \"{session_id}\"")
    else:
        print(f"\n❌ Échec de la création de la session")
