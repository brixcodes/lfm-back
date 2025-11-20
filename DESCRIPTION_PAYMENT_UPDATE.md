# Mise à Jour des Descriptions de Paiement

## Modifications Appliquées

### 1. Descriptions Spécifiques par Type de Paiement

Les descriptions sont maintenant générées automatiquement selon le type de payable :

- **Inscription** (`StudentApplication`) : `"paiement des frais inscription"`
- **Formation** (`StudentApplication` avec "formation" dans la description) : `"paiement des frais de formation"`
- **Offre Emploi** (`JobApplication`) : `"paiement des frais offre emploi"`
- **Cabinet Recrutement** (`CabinetApplication`) : `"paiement des frais candidature cabinet"`

### 2. Nettoyage des Caractères Spéciaux

Toutes les descriptions sont nettoyées pour retirer les caractères spéciaux non autorisés par CinetPay :
- Suppression des apostrophes
- Suppression des parenthèses
- Suppression des autres caractères spéciaux
- Conservation des lettres, chiffres, espaces, tirets simples et points

### 3. Logique de Détection

La logique détecte automatiquement le type de paiement :
1. Vérifie d'abord si "formation" ou "training" est présent dans la description ou le type
2. Si c'est un `StudentApplication`, vérifie si c'est une formation ou une inscription
3. Utilise le mapping selon le type de payable
4. Nettoie la description pour retirer les caractères spéciaux

## Exemples

### Inscription
```python
payable_type = "StudentApplication"
description = "Inscription"
→ "paiement des frais inscription"
```

### Formation
```python
payable_type = "StudentApplication"
description = "Formation d'Auxiliaires"
→ "paiement des frais de formation"
```

### Offre Emploi
```python
payable_type = "JobApplication"
→ "paiement des frais offre emploi"
```

### Cabinet Recrutement
```python
payable_type = "CabinetApplication"
→ "paiement des frais candidature cabinet"
```

## Avantages

✅ **Descriptions claires et cohérentes** pour chaque type de paiement
✅ **Pas de caractères spéciaux** qui pourraient causer des erreurs
✅ **Détection automatique** du type de paiement
✅ **Logs détaillés** pour le diagnostic

## Test Recommandé

Tester un paiement Mobile Money avec chaque type de payable pour vérifier que les descriptions sont correctes.

