# Configuration CinetPay via .env

## 📝 Variables d'Environnement Requises

Le système charge automatiquement les credentials CinetPay depuis le fichier `.env`. 

### Configuration dans .env

Ajoutez les lignes suivantes dans votre fichier `.env` (lignes 71-73 ou ailleurs) :

```env
CINETPAY_API_KEY=42570827068a9b0ab138595.83080865
CINETPAY_SITE_ID=105905542
CINETPAY_SECRET_KEY=176118419568a9b10a66c829.71997677
```

### Variables Optionnelles

```env
# URLs de notification et retour
CINETPAY_NOTIFY_URL=https://api.lafaom-mao.org/api/v1/payments/cinetpay/notify
CINETPAY_RETURN_URL=https://lafaom.vertex-cam.com

# Devise par défaut
CINETPAY_CURRENCY=XAF

# Canaux de paiement (ALL, MOBILE_MONEY, CREDIT_CARD, WALLET)
CINETPAY_CHANNELS=ALL
```

## ✅ Vérification

Le système vérifie automatiquement que les credentials sont configurés. Si les valeurs sont manquantes ou vides, vous recevrez une erreur claire indiquant quelle variable manque.

## 🔒 Sécurité

- ⚠️ **Ne commitez JAMAIS** le fichier `.env` dans Git
- ✅ Le fichier `.env` est déjà dans `.gitignore`
- ✅ Les credentials sont chargés automatiquement au démarrage de l'application

## 📋 Format du .env

```env
# CinetPay Configuration (lignes 71-73)
CINETPAY_API_KEY=votre_api_key_ici
CINETPAY_SITE_ID=votre_site_id_ici
CINETPAY_SECRET_KEY=votre_secret_key_ici
```

## 🚀 Après Configuration

1. Redémarrez l'application pour charger les nouvelles variables
2. Les credentials seront automatiquement utilisés par le service CinetPay
3. Vérifiez les logs au démarrage pour confirmer le chargement

