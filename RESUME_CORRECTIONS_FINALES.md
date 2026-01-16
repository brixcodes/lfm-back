# Résumé des corrections finales

## 🔍 Problèmes identifiés

La base de données `student_attachments` a une structure différente du modèle Python:

### Colonnes dans la DB:
- `application_id` ✅
- `attachment_type` (pas `document_type`)
- `file_name` (manquait dans le modèle)
- `file_path` ✅
- `upload_date` ✅

### Colonnes dans le modèle Python (avant correction):
- `application_id` ✅
- `document_type` ❌ (devrait être `attachment_type`)
- `file_path` ✅
- `upload_date` ✅
- `file_name` ❌ (manquait)

## ✅ Corrections apportées

### 1. Modèle `StudentAttachment` (`src/api/training/models.py`)

```python
class StudentAttachment(CustomBaseModel, table=True):
    __tablename__ = "student_attachments"

    application_id: int = Field(foreign_key="student_applications.id", nullable=False)
    attachment_type: str = Field(max_length=100)  # ✅ Correspond à la DB
    file_name: str = Field(max_length=255)  # ✅ Ajouté
    file_path: str = Field(max_length=255)
    upload_date: Optional[datetime] = Field(default=None)
    
    # Alias pour compatibilité avec le code existant
    @property
    def document_type(self) -> str:
        return self.attachment_type
    
    @document_type.setter
    def document_type(self, value: str):
        self.attachment_type = value
```

### 2. Service `create_student_attachment` (`src/api/training/services/student_application.py`)

```python
# Extraire le nom du fichier
file_name = input.file.filename if hasattr(input.file, 'filename') else input.name

attachment = StudentAttachment(
    application_id=application_id, 
    file_path=url, 
    attachment_type=document_type,  # ✅ Utilise attachment_type
    file_name=file_name  # ✅ Ajouté
)
```

### 3. Router `create_student_attachment` (`src/api/training/routers/student_application.py`)

```python
@router.post("/my-student-applications/{application_id}/attachments")
async def create_student_attachment(
    application_id: int,
    name: Annotated[str, Form(...)],  # ✅ Paramètre direct
    file: Annotated[UploadFile, File(...)],  # ✅ Paramètre direct
    student_app_service: StudentApplicationService = Depends(),
):
    # ...
    input_data = StudentAttachmentInput(name=name, file=file)
    # ...
```

## 🧪 Test

```bash
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=BANK_TRANSFER_RECEIPT" \
  -F "file=@test.pdf"
```

**Réponse attendue**:
```json
{
  "success": true,
  "message": "Attachment created successfully",
  "data": {
    "id": 1,
    "application_id": 7,
    "document_type": "BANK_TRANSFER_RECEIPT",
    "file_name": "test.pdf",
    "file_path": "https://...s3.amazonaws.com/.../test.pdf",
    "created_at": "2026-01-16T19:30:00",
    "updated_at": "2026-01-16T19:30:00"
  }
}
```

## 📋 Workflow complet

### 1. Créer une candidature
```bash
curl -X POST "http://localhost:8000/api/v1/student-applications" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "target_session_id": "session-id",
    "first_name": "John",
    "last_name": "Doe",
    "payment_method": "TRANSFER"
  }'
```

### 2. Uploader le reçu bancaire
```bash
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=BANK_TRANSFER_RECEIPT" \
  -F "file=@receipt.pdf"
```

### 3. Uploader d'autres documents
```bash
curl -X POST "http://localhost:8000/api/v1/my-student-applications/7/attachments" \
  -F "name=CV" \
  -F "file=@cv.pdf"
```

### 4. Vérifier les attachments
```bash
curl -X GET "http://localhost:8000/api/v1/my-student-applications/7/attachments"
```

## ✨ Avantages

1. ✅ Le modèle correspond maintenant exactement à la structure de la DB
2. ✅ Pas besoin de migration SQL
3. ✅ Le code existant continue de fonctionner grâce aux propriétés `document_type`
4. ✅ Le nom du fichier est maintenant sauvegardé
5. ✅ Upload de fichiers fonctionne avec `multipart/form-data`

## 🎯 Types de documents supportés

- `BANK_TRANSFER_RECEIPT` - Reçu de virement bancaire (obligatoire pour TRANSFER)
- `CV` - Curriculum Vitae
- `DIPLOMA` - Diplôme
- `MOTIVATION_LETTER` - Lettre de motivation
- `ID_CARD` - Carte d'identité
- `PASSPORT` - Passeport
- `TRANSCRIPT` - Relevé de notes
- Tout autre type personnalisé

## 📝 Notes importantes

- Le champ `name` dans la requête définit le `attachment_type` (ex: "BANK_TRANSFER_RECEIPT")
- Le `file_name` est extrait automatiquement du fichier uploadé
- Le `file_path` est l'URL S3 retournée par `FileHelper.upload_file()`
- La propriété `document_type` est un alias pour `attachment_type` pour la compatibilité
