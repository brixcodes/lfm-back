# Route DELETE /api/v1/student-applications/{application_id}

## 🎯 Description

Route admin pour supprimer une candidature étudiante spécifique par son ID.

## 🔐 Permissions requises

- Permission: `CAN_VIEW_STUDENT_APPLICATION`
- Rôle: Admin uniquement

## 📋 Endpoint

```
DELETE /api/v1/student-applications/{application_id}
```

## 🔑 Headers

```
Authorization: Bearer {admin_token}
```

## 📤 Paramètres

- `application_id` (path, required): ID de la candidature à supprimer

## 📥 Réponse

### Succès (200 OK)

```json
{
  "success": true,
  "message": "Student application deleted successfully",
  "data": {
    "id": 7,
    "user_id": "user-uuid",
    "training_id": "training-uuid",
    "target_session_id": "session-uuid",
    "application_number": "APP-TRAIN-0001-20260116180000",
    "status": "RECEIVED",
    "payment_method": "TRANSFER",
    "created_at": "2026-01-16T18:00:00",
    "updated_at": "2026-01-16T18:00:00"
  }
}
```

### Erreur - Candidature non trouvée (404 Not Found)

```json
{
  "message": "Student application not found",
  "error_code": "STUDENT_APPLICATION_NOT_FOUND",
  "success": false
}
```

### Erreur - Non autorisé (403 Forbidden)

```json
{
  "message": "Permission denied",
  "error_code": "permission_denied",
  "success": false
}
```

## 🧪 Exemples d'utilisation

### Avec cURL

```bash
curl -X DELETE "http://localhost:8000/api/v1/student-applications/7" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Avec Python (requests)

```python
import requests

application_id = 7
url = f"http://localhost:8000/api/v1/student-applications/{application_id}"
headers = {
    "Authorization": "Bearer YOUR_ADMIN_TOKEN"
}

response = requests.delete(url, headers=headers)
print(response.json())
```

### Avec JavaScript (fetch)

```javascript
const applicationId = 7;

fetch(`http://localhost:8000/api/v1/student-applications/${applicationId}`, {
  method: 'DELETE',
  headers: {
    'Authorization': 'Bearer YOUR_ADMIN_TOKEN'
  }
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Erreur:', error));
```

## ⚙️ Fonctionnement

1. Vérifie que la candidature existe
2. Dissocie les attachments (met `application_id` à NULL dans `student_attachments`)
3. Supprime la candidature de la base de données
4. Retourne la candidature supprimée

## ⚠️ Avertissements

1. **Action irréversible**: La candidature supprimée ne peut pas être récupérée
2. **Attachments**: Les fichiers attachés sont dissociés mais pas supprimés du stockage
3. **Cascade**: Les relations liées peuvent être affectées

## 🔄 Routes similaires

### Pour l'utilisateur (étudiant)
```
DELETE /api/v1/my-student-applications/{application_id}
```
- L'utilisateur peut supprimer uniquement ses propres candidatures
- Restrictions: Ne peut pas supprimer si `status = APPROVED` ou `REFUSED`

### Pour l'admin
```
DELETE /api/v1/student-applications/{application_id}
```
- L'admin peut supprimer n'importe quelle candidature
- Aucune restriction de statut

## 📝 Notes

- Les candidatures avec n'importe quel statut peuvent être supprimées par l'admin
- Les paiements associés ne sont PAS supprimés automatiquement
- Les participants inscrits (`training_session_participants`) ne sont PAS supprimés automatiquement

## 🛡️ Sécurité

- Authentification requise
- Permission admin requise (`CAN_VIEW_STUDENT_APPLICATION`)
- Validation de l'existence de la candidature

## 💡 Exemple de workflow

```bash
# 1. Lister toutes les candidatures
curl -X GET "http://localhost:8000/api/v1/student-applications" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 2. Supprimer une candidature spécifique
curl -X DELETE "http://localhost:8000/api/v1/student-applications/7" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 3. Vérifier que la candidature a été supprimée
curl -X GET "http://localhost:8000/api/v1/student-applications/7" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
# Devrait retourner 404
```
