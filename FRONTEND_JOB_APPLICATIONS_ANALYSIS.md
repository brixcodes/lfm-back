# Analyse Frontend : Candidatures d'emploi

## Problème Identifié

Après correction du backend, le frontend devrait maintenant afficher correctement les candidatures payées. Voici l'analyse du code frontend :

## Code Frontend

### 1. **Service API** (`src/services/api/job-offers.ts`)

Le service appelle l'endpoint `/job-applications` :

```typescript
async getJobApplications(params?: {
  page?: number
  page_size?: number
  search?: string
  status?: string
  is_paid?: boolean  // ✅ Paramètre disponible
  job_offer_id?: string
  order_by?: 'created_at' | 'application_number' | 'status'
  asc?: 'asc' | 'desc'
}): Promise<JobApplicationsPageOutSuccess> {
  const response = await apiService.get('/job-applications', { params })
  return response as JobApplicationsPageOutSuccess
}
```

### 2. **Page JobApplications** (`src/pages/jobs/JobApplications.vue`)

La page charge les candidatures sans passer explicitement `is_paid` :

```typescript
const loadApplications = async () => {
  const requestParams: any = {
    page: 1,
    page_size: 10000,
    order_by: 'created_at',
    asc: 'desc'
  }
  // ❌ Pas de paramètre is_paid explicite
  await jobOffersStore.getJobApplications(requestParams)
  allApplications.value = [...jobOffersStore.jobApplications]
}
```

### 3. **Backend Router** (`lafaom_backend/src/api/job_offers/router.py`)

Le backend force `is_paid=True` par défaut :

```python
@router.get("/job-applications", response_model=JobApplicationsPageOutSuccess)
async def list_job_applications(
    filters: Annotated[JobApplicationFilter, Query(...)],
    ...
):
    """Get only 'paid' job applications by default (TRANSFER all + ONLINE paid)"""
    # Force is_paid to True by default for the main endpoint
    if filters.is_paid is None:
        filters.is_paid = True  # ✅ Force les candidatures payées par défaut
    applications, total = await job_offer_service.list_job_applications(filters)
    return {"data": applications, ...}
```

## Conclusion

### ✅ Le Frontend est Correct

Le frontend n'a **pas besoin de modification** car :

1. **Le backend force `is_paid=True` par défaut** : Même si le frontend ne passe pas explicitement `is_paid`, le backend retourne uniquement les candidatures payées.

2. **Le problème était uniquement dans le backend** : La mise à jour du `payment_id` échouait silencieusement, donc les candidatures payées n'avaient pas leur `payment_id` mis à jour et n'apparaissaient pas dans la liste.

3. **Avec la correction backend** : Maintenant que le `payment_id` est correctement mis à jour après un paiement réussi, les candidatures apparaîtront automatiquement dans la liste.

## Vérification du Statut de Paiement dans le Frontend

Le frontend vérifie correctement le statut de paiement :

```typescript
// Ligne 370-377 de JobApplications.vue
const isPaymentPaid = (application: JobApplication) => {
  // Si payment_method est TRANSFER, considérer comme payé
  if ((application as any).payment_method === 'TRANSFER') {
    return true
  }
  // Sinon, utiliser la logique basée sur payment_id
  return !!application.payment_id  // ✅ Vérifie si payment_id existe
}
```

Cette logique est correcte et correspond à la logique backend :
- `TRANSFER` → Toujours payé
- `ONLINE` → Payé si `payment_id IS NOT NULL`

## Résultat Attendu

Après la correction du backend :

1. ✅ Le webhook CinetPay met à jour correctement le `payment_id` dans `JobApplication`
2. ✅ Le backend retourne uniquement les candidatures payées (`is_paid=True` par défaut)
3. ✅ Le frontend affiche correctement les candidatures dans "Candidatures d'emploi"
4. ✅ Le statut de paiement est correctement affiché (Payé/Non payé)

## Test

Pour vérifier que tout fonctionne :

1. Soumettre une nouvelle candidature d'emploi
2. Effectuer le paiement via CinetPay
3. Vérifier que le webhook met à jour le `payment_id` (logs backend)
4. Actualiser la page "Candidatures d'emploi" dans le frontend
5. La candidature devrait apparaître dans la liste

## Note

Si vous souhaitez afficher **toutes** les candidatures (payées et non payées) dans le frontend, vous pouvez :

1. Utiliser l'endpoint `/job-applications/all` qui retourne toutes les candidatures
2. Ou passer explicitement `is_paid: null` dans les paramètres

Mais par défaut, l'endpoint `/job-applications` retourne uniquement les candidatures payées, ce qui est le comportement attendu pour la page "Candidatures d'emploi".

