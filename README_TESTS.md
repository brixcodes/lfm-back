# Guide d'Exécution des Tests de Paiement

## 📋 Tests Disponibles

Deux scripts de test ont été créés pour simuler le processus complet de paiement jusqu'à la validation:

### 1. `test_payment_simulation.py` - Tests Interactifs
Script interactif qui permet de tester les paiements avec l'API réelle de CinetPay.

### 2. `test_payment_end_to_end.py` - Tests Automatisés
Tests automatisés avec mocks pour tester le flux complet sans appeler l'API réelle.

## 🚀 Exécution des Tests

### Option 1: Tests Interactifs (API Réelle)

```bash
cd lafaom_backend
python test_payment_simulation.py
```

Ce script vous permettra de:
- Tester un paiement Mobile Money avec le numéro: `+237657807309`
- Tester un paiement par carte bancaire avec:
  - Numéro: `4834 5600 7033 2785`
  - Expiration: `05/26`
  - CVV: `329`
- Vérifier le statut d'une transaction existante

**⚠️ Important**: Ces tests utilisent l'API réelle de CinetPay. Assurez-vous que:
- Vos credentials sont configurés dans `.env`
- Vous avez un compte de test CinetPay
- Vous êtes prêt à valider le paiement sur votre téléphone/carte

### Option 2: Tests Automatisés (Avec Mocks)

```bash
cd lafaom_backend
pytest test_payment_end_to_end.py -v -s
```

Ces tests simulent le processus complet sans appeler l'API réelle:
- ✅ Test du flux Mobile Money complet
- ✅ Test du flux Carte Bancaire complet
- ✅ Vérification de tous les champs requis
- ✅ Simulation des différents statuts (en attente → accepté)

## 📝 Informations de Test

### Mobile Money
- **Numéro**: `+237657807309`
- **Montant de test**: 10000 XAF

### Carte Bancaire
- **Numéro**: `4834 5600 7033 2785`
- **Expiration**: `05/26`
- **CVV**: `329`
- **Montant de test**: 10000 XAF

## 🔍 Ce que les Tests Vérifient

### 1. Initialisation du Paiement
- ✅ Création de la transaction
- ✅ Génération du lien de paiement
- ✅ Validation des paramètres requis
- ✅ Format correct du transaction_id
- ✅ Nettoyage de la description

### 2. Validation des Champs
- ✅ Tous les champs obligatoires pour Mobile Money
- ✅ Tous les champs obligatoires pour Carte Bancaire
- ✅ Format correct du numéro de téléphone
- ✅ Format correct des informations client

### 3. Vérification du Statut
- ✅ Statut en attente (WAITING_FOR_CUSTOMER)
- ✅ Statut accepté (ACCEPTED)
- ✅ Gestion des erreurs
- ✅ Récupération des détails de la transaction

## 📊 Résultats Attendus

### Mobile Money
1. **Initialisation**: ✅ Succès avec lien de paiement
2. **Statut initial**: ⏳ WAITING_FOR_CUSTOMER
3. **Après validation**: ✅ ACCEPTED avec méthode "OM" (Orange Money)

### Carte Bancaire
1. **Initialisation**: ✅ Succès avec lien de paiement
2. **Statut initial**: ⏳ WAITING_FOR_CUSTOMER
3. **Après validation**: ✅ ACCEPTED avec méthode "VISAM" ou "MASTERCARD"

## 🐛 Dépannage

### Erreur: "CinetPay API Key is not configured"
- Vérifiez que vos credentials sont dans le fichier `.env`
- Vérifiez que les variables sont correctement nommées

### Erreur: "Connection failed"
- Vérifiez votre connexion internet
- Vérifiez que l'API CinetPay est accessible

### Le paiement reste en attente
- C'est normal si vous n'avez pas validé le paiement
- Utilisez le script interactif pour valider manuellement
- Vérifiez le statut avec l'option 3 du script interactif

## 📚 Documentation

Pour plus d'informations sur l'intégration CinetPay, consultez:
- `CINETPAY_INTEGRATION_COMPLETE.md` - Documentation complète
- `CINETPAY_IMPROVEMENTS_SUMMARY.md` - Résumé des améliorations
- `CINETPAY_ENV_SETUP.md` - Configuration des variables d'environnement

