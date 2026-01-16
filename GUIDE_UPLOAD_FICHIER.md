# Guide d'upload de fichiers pour les attachments

## ❌ Ce qui ne fonctionne PAS

### Erreur 1: Utiliser JSON pour uploader un fichier
```bash
# ❌ INCORRECT
curl -X 'POST' \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d '{
    "name": "BANK_TRANSFER_RECEIPT",
    "file": {
      "name": "AGL.pdf",
      "type": "application/pdf"
    }
  }'
```

**Problème**: Tu ne peux pas envoyer un fichier en JSON. Il faut utiliser `multipart/form-data`.

## ✅ La bonne méthode

### Méthode 1: Avec cURL (RECOMMANDÉ)

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -H 'accept: application/json' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@/chemin/vers/AGL.pdf'
```

**Points importants**:
- Utilise `-F` (form) au lieu de `-d` (data)
- Le fichier doit être précédé de `@` suivi du chemin complet
- Pas besoin de spécifier `Content-Type`, cURL le fait automatiquement avec `-F`

### Méthode 2: Avec Postman

1. Ouvre Postman
2. Sélectionne `POST` et l'URL: `http://localhost:8000/api/v1/my-student-applications/7/attachments`
3. Va dans l'onglet **Body**
4. Sélectionne **form-data** (pas raw, pas x-www-form-urlencoded)
5. Ajoute les champs:
   - Key: `name`, Value: `BANK_TRANSFER_RECEIPT`, Type: **Text**
   - Key: `file`, Value: Clique sur "Select Files" et choisis ton fichier, Type: **File**
6. Clique sur **Send**

### Méthode 3: Avec Python (requests)

```python
import requests

url = "http://localhost:8000/api/v1/my-student-applications/7/attachments"

# Ouvrir le fichier en mode binaire
with open("/chemin/vers/AGL.pdf", "rb") as f:
    files = {
        "file": ("AGL.pdf", f, "application/pdf")
    }
    data = {
        "name": "BANK_TRANSFER_RECEIPT"
    }
    
    response = requests.post(url, data=data, files=files)
    print(response.json())
```

### Méthode 4: Avec JavaScript (fetch)

```javascript
// Dans un formulaire HTML avec <input type="file" id="fileInput">
const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];

const formData = new FormData();
formData.append('name', 'BANK_TRANSFER_RECEIPT');
formData.append('file', file);

fetch('http://localhost:8000/api/v1/my-student-applications/7/attachments', {
  method: 'POST',
  body: formData
  // Ne pas définir Content-Type, le navigateur le fait automatiquement
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Erreur:', error));
```

### Méthode 5: Avec JavaScript (axios)

```javascript
import axios from 'axios';

const fileInput = document.getElementById('fileInput');
const file = fileInput.files[0];

const formData = new FormData();
formData.append('name', 'BANK_TRANSFER_RECEIPT');
formData.append('file', file);

axios.post('http://localhost:8000/api/v1/my-student-applications/7/attachments', formData, {
  headers: {
    'Content-Type': 'multipart/form-data'
  }
})
.then(response => console.log(response.data))
.catch(error => console.error('Erreur:', error));
```

## 📋 Schéma de l'endpoint

L'endpoint attend:

```python
@router.post("/my-student-applications/{application_id}/attachments")
async def create_student_attachment(
    application_id: int,
    input: Annotated[StudentAttachmentInput, Form(...)],  # Form, pas Body!
    ...
)

class StudentAttachmentInput(BaseModel):
    name: str          # Type de document (ex: "BANK_TRANSFER_RECEIPT")
    file: UploadFile   # Le fichier à uploader
```

**Important**: C'est un `Form(...)`, pas un `Body(...)`, donc il faut utiliser `multipart/form-data`.

## 🧪 Test complet avec cURL

```bash
# 1. Créer une candidature avec paiement TRANSFER
APPLICATION_RESPONSE=$(curl -X 'POST' \
  'http://localhost:8000/api/v1/student-applications' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "test@example.com",
    "target_session_id": "votre-session-id",
    "first_name": "Jean",
    "last_name": "Dupont",
    "phone_number": "+237600000000",
    "country_code": "CM",
    "payment_method": "TRANSFER",
    "attachments": []
  }')

# Extraire l'ID de la candidature
APPLICATION_ID=$(echo $APPLICATION_RESPONSE | jq -r '.data.id')
echo "Candidature créée avec ID: $APPLICATION_ID"

# 2. Uploader le reçu bancaire
curl -X 'POST' \
  "http://localhost:8000/api/v1/my-student-applications/$APPLICATION_ID/attachments" \
  -H 'accept: application/json' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@./recu_bancaire.pdf'

# 3. Uploader le CV
curl -X 'POST' \
  "http://localhost:8000/api/v1/my-student-applications/$APPLICATION_ID/attachments" \
  -H 'accept: application/json' \
  -F 'name=CV' \
  -F 'file=@./cv.pdf'

# 4. Vérifier les attachments
curl -X 'GET' \
  "http://localhost:8000/api/v1/my-student-applications/$APPLICATION_ID/attachments" \
  -H 'accept: application/json'
```

## 🎯 Exemples de commandes cURL correctes

### Uploader un reçu bancaire
```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@/Users/john/Documents/recu.pdf'
```

### Uploader un CV
```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=CV' \
  -F 'file=@/Users/john/Documents/cv.pdf'
```

### Uploader un diplôme
```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=DIPLOMA' \
  -F 'file=@/Users/john/Documents/diploma.pdf'
```

### Avec authentification (si nécessaire)
```bash
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@/Users/john/Documents/recu.pdf'
```

## 📝 Types de fichiers acceptés

L'API accepte généralement:
- PDF: `.pdf`
- Images: `.jpg`, `.jpeg`, `.png`
- Documents: `.doc`, `.docx`

Vérifie la configuration de ton serveur pour les limites de taille.

## ⚠️ Erreurs courantes

### Erreur 1: "Field required"
**Cause**: Tu utilises JSON au lieu de form-data
**Solution**: Utilise `-F` avec cURL ou form-data avec Postman

### Erreur 2: "File not found"
**Cause**: Le chemin du fichier est incorrect
**Solution**: Utilise le chemin absolu du fichier

### Erreur 3: "Invalid file type"
**Cause**: Le type de fichier n'est pas accepté
**Solution**: Vérifie que tu uploades un PDF ou une image

## 🔍 Vérifier que ça fonctionne

Après l'upload, tu devrais recevoir une réponse comme:

```json
{
  "success": true,
  "message": "Attachment created successfully",
  "data": {
    "id": 123,
    "application_id": 7,
    "document_type": "BANK_TRANSFER_RECEIPT",
    "file_path": "/uploads/student-applications/7/BANK_TRANSFER_RECEIPT_123.pdf",
    "created_at": "2026-01-16T18:00:00",
    "updated_at": "2026-01-16T18:00:00"
  }
}
```

## 💡 Conseil

Pour tester rapidement, crée un fichier PDF de test:

```bash
# Créer un fichier PDF de test
echo "Test receipt" > test.txt
# Sur macOS/Linux, tu peux convertir en PDF avec:
# enscript -p test.ps test.txt && ps2pdf test.ps test.pdf

# Ou simplement utilise n'importe quel PDF existant
curl -X POST \
  'http://localhost:8000/api/v1/my-student-applications/7/attachments' \
  -F 'name=BANK_TRANSFER_RECEIPT' \
  -F 'file=@test.pdf'
```
