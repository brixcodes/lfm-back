# Solution finale - Student Attachments

## 🎯 Problème résolu

La table `student_attachments` dans la base de données a des colonnes dupliquées et des noms différents du modèle Python.

## 📊 Structure réelle de la table

```
student_attachments:
├── id (PK)
├── created_at
├── updated_at
├── delete_at
├── application_id (FK → student_applications.id)
├── attachment_type (NOT NULL) ← Colonne dupliquée
├── document_type (NOT NULL) ← Colonne dupliquée
├── file_name (NOT NULL)
├── file_path (NOT NULL)
└── upload_date (NULLABLE)
```

## ✅ Solution appliquée

### 1. Modèle Python mis à jour

```python
class StudentAttachment(CustomBaseModel, table=True):
    __tablename__ = "student_attachments"

    application_id: int = Field(foreign_key="student_applications.id", nullable=False)
    attachment_type: str = Field(max_length=100)  # Colonne DB
    document_type: str = Field(max_length=100)  # Colonne DB (dupliquée)
    file_name: str = Field(max_length=255)
    file_path: str = Field(max_length=255)
    upload_date: Optional[datetime] = Field(default=None)
```

### 2. Service mis à jour

```python
attachment = StudentAttachment(
    application_id=application_id, 
    file_path=url, 
    attachment_type=document_type,  # Remplir les deux
    document_type=document_type,  # colonnes avec la même valeur
    file_name=file_name
)
```

## 🧪 Test

```bash
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=BANK_TRANSFER_RECEIPT" \
  -F "file=@test.pdf"
```

**Devrait maintenant fonctionner!** ✅

## 📋 Workflow complet

### 1. Créer une candidature (TRANSFER)

```bash
curl -X POST "http://localhost:8000/api/v1/student-applications" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "target_session_id": "your-session-id",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+237600000000",
    "country_code": "CM",
    "payment_method": "TRANSFER"
  }'
```

**Réponse**:
```json
{
  "success": true,
  "message": "Student application created successfully. Please upload the bank transfer receipt.",
  "data": {
    "id": 7,
    "application_number": "APP-TRAIN-0001-...",
    "status": "RECEIVED",
    "payment_method": "TRANSFER"
  }
}
```

### 2. Uploader le reçu bancaire

```bash
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=BANK_TRANSFER_RECEIPT" \
  -F "file=@receipt.pdf"
```

**Réponse**:
```json
{
  "success": true,
  "message": "Attachment created successfully",
  "data": {
    "id": 1,
    "application_id": 7,
    "document_type": "BANK_TRANSFER_RECEIPT",
    "file_name": "receipt.pdf",
    "file_path": "https://...s3.amazonaws.com/.../receipt.pdf",
    "created_at": "2026-01-16T19:30:00"
  }
}
```

### 3. Uploader d'autres documents (optionnel)

```bash
# CV
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=CV" \
  -F "file=@cv.pdf"

# Diplôme
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=DIPLOMA" \
  -F "file=@diploma.pdf"
```

### 4. Vérifier les attachments

```bash
curl -X GET "http://localhost:8000/api/v1/my-student-applications/7/attachments"
```

## 🔄 Pour paiement ONLINE

```bash
curl -X POST "http://localhost:8000/api/v1/student-applications" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "target_session_id": "your-session-id",
    "first_name": "John",
    "last_name": "Doe",
    "payment_method": "ONLINE"
  }'
```

**Réponse inclut le lien de paiement**:
```json
{
  "success": true,
  "message": "Student application created successfully",
  "data": {
    "id": 8,
    "payment": {
      "payment_link": "https://checkout.cinetpay.com/...",
      "transaction_id": "...",
      "amount": 50000
    }
  }
}
```

## 🎯 Types de documents

- `BANK_TRANSFER_RECEIPT` - Reçu bancaire (obligatoire pour TRANSFER)
- `CV` - Curriculum Vitae
- `DIPLOMA` - Diplôme
- `MOTIVATION_LETTER` - Lettre de motivation
- `ID_CARD` - Carte d'identité
- `PASSPORT` - Passeport
- `TRANSCRIPT` - Relevé de notes

## 🧹 Nettoyage futur (optionnel)

Une fois que tout fonctionne, tu peux nettoyer la table pour supprimer les colonnes dupliquées.

Voir le fichier `nettoyage_futur.sql` pour les instructions.

**Recommandation**: Garde `document_type` et supprime `attachment_type` car c'est plus standard.

## ✨ Résumé des modifications

1. ✅ Ajout de `file_name` au modèle
2. ✅ Ajout de `attachment_type` ET `document_type` au modèle
3. ✅ Les deux colonnes sont remplies avec la même valeur
4. ✅ Le nom du fichier est extrait automatiquement
5. ✅ Upload fonctionne avec `multipart/form-data`
6. ✅ Pas besoin de migration SQL immédiate

## 📝 Fichiers modifiés

- `src/api/training/models.py` - Modèle StudentAttachment
- `src/api/training/services/student_application.py` - Service create_student_attachment
- `src/api/training/routers/student_application.py` - Router create_student_attachment
- `src/api/training/schemas.py` - Schéma StudentAttachmentOut

## 🎉 Ça devrait fonctionner maintenant!

Teste avec:
```bash
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=BANK_TRANSFER_RECEIPT" \
  -F "file=@ton_fichier.pdf"
```
