# Guide: Upload de documents pour candidature étudiante

## 🎯 Processus en 2 étapes (OBLIGATOIRE)

### Étape 1: Créer la candidature SANS attachments

**Endpoint**: `POST /api/v1/student-applications`

**Body (JSON)**:
```json
{
  "email": "kseme277@gmail.com",
  "target_session_id": "6c13084c-b7d2-4bad-96d8-eacad84725d9",
  "first_name": "Koffi",
  "last_name": "Seme",
  "phone_number": "+221771234567",
  "country_code": "SN",
  "payment_method": "TRANSFER"
}
```

**Réponse**:
```json
{
  "success": true,
  "message": "Student application created successfully. Please upload the bank transfer receipt.",
  "data": {
    "id": 123,
    "application_number": "APP-TRAIN-0001-20260116180000",
    "status": "RECEIVED",
    "attachments": []
  }
}
```

### Étape 2: Uploader les documents

**Endpoint**: `POST /api/v1/my-student-applications/{application_id}/attachments`

**Type**: `multipart/form-data`

**Exemple cURL**:
```bash
curl -X POST "http://api.com/api/v1/my-student-applications/123/attachments" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "name=BANK_TRANSFER_RECEIPT" \
  -F "file=@/path/to/receipt.pdf"
```

**Exemple Postman**:
1. Method: POST
2. URL: `/api/v1/my-student-applications/123/attachments`
3. Body → form-data:
   - Key: `name`, Value: `BANK_TRANSFER_RECEIPT` (Text)
   - Key: `file`, Value: Sélectionner le fichier (File)

## ✅ Types de documents

- `BANK_TRANSFER_RECEIPT` - Reçu bancaire (obligatoire pour TRANSFER)
- `CV` - Curriculum Vitae
- `DIPLOMA` - Diplôme
- `ID_CARD` - Carte d'identité
- `TRANSCRIPT` - Relevé de notes
