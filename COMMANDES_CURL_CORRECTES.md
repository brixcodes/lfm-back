# Commandes cURL correctes pour l'upload d'attachments

## 🎯 La commande correcte

### Pour uploader un fichier avec cURL

```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -H 'accept: application/json' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@/chemin/vers/ton/fichier.pdf'
```

## 🔑 Points clés

1. **Utilise `-F` (form) au lieu de `-d` (data)**
   - `-F` = multipart/form-data (pour les fichiers)
   - `-d` = application/json (pour les données JSON)

2. **Le fichier doit être précédé de `@`**
   - `@` indique à cURL que c'est un fichier à uploader
   - Exemple: `file=@/Users/john/Documents/recu.pdf`

3. **Pas besoin de spécifier `Content-Type`**
   - cURL le fait automatiquement avec `-F`

4. **Le chemin du fichier doit être absolu ou relatif**
   - Absolu: `/Users/john/Documents/recu.pdf`
   - Relatif: `./recu.pdf` (fichier dans le dossier courant)

## 📋 Exemples complets

### Exemple 1: Uploader un reçu bancaire

```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@./recu_bancaire.pdf'
```

### Exemple 2: Uploader un CV

```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=CV' \
  -F 'file=@./cv.pdf'
```

### Exemple 3: Uploader un diplôme

```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=DIPLOMA' \
  -F 'file=@./diplome.pdf'
```

### Exemple 4: Avec authentification

```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@./recu.pdf'
```

## ❌ Ce qui NE fonctionne PAS

### Erreur 1: Utiliser `-d` avec JSON
```bash
# ❌ INCORRECT
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "BANK_TRANSFER_RECEIPT",
    "file": "fichier.pdf"
  }'
```

### Erreur 2: Oublier le `@` devant le fichier
```bash
# ❌ INCORRECT
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=recu.pdf'  # Manque le @
```

### Erreur 3: Utiliser `application/x-www-form-urlencoded`
```bash
# ❌ INCORRECT
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'name=BANK_TRANSFER_RECEIPT&file=...'
```

## 🧪 Test rapide

### Étape 1: Créer un fichier de test
```bash
echo "Test receipt" > test_receipt.txt
```

### Étape 2: Uploader le fichier
```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@test_receipt.txt'
```

### Étape 3: Vérifier la réponse
Tu devrais recevoir:
```json
{
  "success": true,
  "message": "Attachment created successfully",
  "data": {
    "id": 123,
    "application_id": 7,
    "document_type": "BANK_TRANSFER_RECEIPT",
    "file_path": "/uploads/student-applications/7/BANK_TRANSFER_RECEIPT_123.txt",
    "created_at": "2026-01-16T18:00:00",
    "updated_at": "2026-01-16T18:00:00"
  }
}
```

## 🔄 Workflow complet

### 1. Créer une candidature
```bash
curl -X POST \
  'http://localhost:8000/api/v1/student-applications' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "target_session_id": "session-id",
    "first_name": "Jean",
    "last_name": "Dupont",
    "phone_number": "+237600000000",
    "country_code": "CM",
    "payment_method": "TRANSFER",
    "attachments": []
  }'
```

Réponse:
```json
{
  "success": true,
  "data": {
    "id": 7,
    "application_number": "APP-TRAIN-0007-...",
    ...
  }
}
```

### 2. Uploader le reçu bancaire
```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@./recu.pdf'
```

### 3. Uploader d'autres documents (optionnel)
```bash
# CV
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=CV' \
  -F 'file=@./cv.pdf'

# Diplôme
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=DIPLOMA' \
  -F 'file=@./diplome.pdf'
```

### 4. Vérifier les attachments
```bash
curl -X GET \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments'
```

## 💡 Astuces

### Voir les détails de la requête
Ajoute `-v` pour voir tous les détails:
```bash
curl -v -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@./recu.pdf'
```

### Sauvegarder la réponse dans un fichier
```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments