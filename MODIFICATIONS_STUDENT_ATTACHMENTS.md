# Modifications pour utiliser StudentAttachment au lieu de JobAttachment

## Problème identifié
L'API `POST /api/v1/student-applications` acceptait des attachments dans l'input mais ne les créait pas automatiquement dans la base de données. Les attachments devaient être créés manuellement via l'endpoint séparé `POST /api/v1/my-student-applications/{application_id}/attachments`.

## Solution implémentée

### 1. Modification du service `StudentApplicationService`
**Fichier**: `src/api/training/services/student_application.py`

**Changement**: Ajout de la création automatique des attachments lors de la création d'une candidature étudiante.

```python
# Après la création de l'application, on crée les attachments si fournis
if data.attachments:
    for attachment_input in data.attachments:
        attachment = StudentAttachment(
            application_id=application.id,
            document_type=attachment_input.type,
            file_path=attachment_input.url,
            upload_date=datetime.now()  # Sans timezone pour éviter les conflits avec la DB
        )
        self.session.add(attachment)
    await self.session.commit()
```

### 2. Correction du problème de timezone
**Problème**: Le champ `upload_date` dans la table `student_attachments` est défini comme `TIMESTAMP WITHOUT TIME ZONE`, mais le code essayait d'insérer un `datetime` avec timezone.

**Solution**: Utilisation de `datetime.now()` au lieu de `datetime.now(timezone.utc)` pour éviter le conflit.

## Fonctionnalités vérifiées

### ✅ POST /api/v1/student-applications
- Crée automatiquement les attachments fournis dans l'input
- Les attachments sont de type `StudentAttachment` (pas `JobAttachment`)
- Format de l'input:
```json
{
  "email": "student@example.com",
  "target_session_id": "session-id",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+237600000000",
  "country_code": "CM",
  "payment_method": "ONLINE",
  "attachments": [
    {
      "type": "CV",
      "url": "https://example.com/cv.pdf",
      "name": "CV"
    },
    {
      "type": "DIPLOMA",
      "url": "https://example.com/diploma.pdf",
      "name": "Diploma"
    }
  ]
}
```

### ✅ GET /api/v1/student-applications (Liste Admin)
- Retourne les candidatures avec leurs attachments
- Les attachments sont chargés via `selectinload(StudentApplication.attachments)`
- Format de la réponse inclut:
```json
{
  "data": [
    {
      "id": 1,
      "application_number": "APP-TRAIN-0001-20260116174807",
      "attachments": [
        {
          "id": 1,
          "application_id": 1,
          "document_type": "CV",
          "file_path": "https://example.com/cv.pdf",
          "created_at": "2026-01-16T17:48:07",
          "updated_at": "2026-01-16T17:48:07"
        }
      ]
    }
  ]
}
```

### ✅ GET /api/v1/student-applications/{application_id}
- Retourne une candidature spécifique avec ses attachments
- Utilise `get_full_student_application_by_id` qui charge les relations

### ✅ GET /api/v1/my-student-applications
- Liste les candidatures de l'utilisateur connecté avec leurs attachments

### ✅ POST /api/v1/my-student-applications/{application_id}/attachments
- Permet d'ajouter des attachments supplémentaires après la création
- Utilise déjà `StudentAttachment` correctement

## Modèles utilisés

### StudentAttachment
```python
class StudentAttachment(CustomBaseModel, table=True):
    __tablename__ = "student_attachments"

    application_id: int = Field(foreign_key="student_applications.id", nullable=False)
    document_type: str = Field(max_length=100)
    file_path: str = Field(max_length=255)
    upload_date: Optional[datetime] = Field(default=None)
```

### StudentApplication
```python
class StudentApplication(CustomBaseModel, table=True):
    __tablename__ = "student_applications"
    
    # ... autres champs ...
    
    attachments: List["StudentAttachment"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
```

## Tests recommandés

1. **Créer une candidature avec attachments**
   - Envoyer une requête POST avec des attachments
   - Vérifier que les attachments sont créés dans la DB
   - Vérifier que la réponse inclut les attachments

2. **Récupérer la liste des candidatures**
   - Vérifier que les attachments sont inclus dans la réponse
   - Tester avec et sans filtres

3. **Méthode de paiement TRANSFER**
   - Vérifier que le reçu bancaire (BANK_TRANSFER_RECEIPT) est obligatoire
   - Vérifier que l'erreur est levée si le reçu est manquant

4. **Méthode de paiement ONLINE**
   - Vérifier que les attachments sont créés même sans reçu bancaire
   - Vérifier que le paiement est initié correctement

## Notes importantes

- Le système utilise déjà `StudentAttachment` partout (pas de `JobAttachment` pour les formations)
- Les attachments sont automatiquement supprimés quand une candidature est supprimée (cascade delete)
- Le champ `upload_date` est optionnel et peut être null
- Les champs `created_at` et `updated_at` sont gérés automatiquement par `CustomBaseModel`
