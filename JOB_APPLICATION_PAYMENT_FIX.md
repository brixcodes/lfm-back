# Correction : Candidature d'emploi non visible après paiement

## Problème Identifié

Après avoir effectué un paiement réussi pour une candidature d'emploi via CinetPay, la candidature n'apparaissait pas dans la section "Candidatures d'emploi" du frontend.

## Cause du Problème

Le problème était dans la fonction `check_payment_status` (version async) dans `lafaom_backend/src/api/payments/service.py` :

**Ligne 377 (AVANT - INCORRECT) :**
```python
job_offer = await job_application_service.update_job_application_payment(
    payment_id=int(payment.id),  # ❌ ERREUR: payment.id est un UUID, pas un int
    application_id=payment.payable_id  # ❌ ERREUR: payable_id est une string, pas un int
)
```

### Problèmes spécifiques :

1. **`payment.id` est un UUID** : `Payment` hérite de `CustomBaseUUIDModel`, donc `payment.id` est un UUID (string), pas un entier. Essayer de le convertir en `int()` provoque une erreur.

2. **`payment.payable_id` est une string** : Lors de la création du paiement (ligne 235), `payable_id` est converti en string : `payable_id=str(payment_data.payable.id)`. Mais `update_job_application_payment` attend un `int` pour `application_id`.

3. **La mise à jour échoue silencieusement** : Si la conversion échoue, la mise à jour du `payment_id` dans `JobApplication` ne se fait pas, donc la candidature reste avec `payment_id = NULL` et n'apparaît pas dans la liste des candidatures payées.

## Solution Appliquée

**Ligne 377-381 (APRÈS - CORRECT) :**
```python
if payment.payable_type == "JobApplication":
    job_application_service = JobOfferService(session=self.session)
    # payment.id est un UUID (string), payable_id est une string représentant un int
    job_offer = await job_application_service.update_job_application_payment(
        payment_id=str(payment.id),  # ✅ Convertir UUID en string
        application_id=int(payment.payable_id)  # ✅ Convertir string en int
    )
```

## Vérification

La version synchrone `check_payment_status_sync` (ligne 452) était déjà correcte :
```python
job_application.payment_id = payment.id  # ✅ UUID directement assigné
```

## Résultat

Maintenant, après un paiement réussi :
1. ✅ Le webhook CinetPay appelle `check_payment_status`
2. ✅ Le `payment_id` est correctement mis à jour dans `JobApplication`
3. ✅ La candidature apparaît dans la liste des candidatures payées (`is_paid=True`)
4. ✅ La candidature est visible dans "Candidatures d'emploi" du frontend

## Endpoint Frontend

Le frontend utilise l'endpoint `/job-applications` qui filtre par défaut les candidatures payées :
- `is_paid=True` par défaut (ligne 120-121 du router)
- Les candidatures avec `payment_id IS NOT NULL` sont considérées comme payées

## Test

Pour vérifier que la correction fonctionne :
1. Soumettre une nouvelle candidature d'emploi
2. Effectuer le paiement via CinetPay
3. Vérifier que le webhook met à jour le `payment_id`
4. Vérifier que la candidature apparaît dans "Candidatures d'emploi"

