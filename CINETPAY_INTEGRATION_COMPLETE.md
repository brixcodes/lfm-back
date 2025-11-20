# Intégration Complète CinetPay - Documentation

## ✅ Améliorations Apportées

### 1. **Mise à Jour des Credentials**
- ✅ API Key: `42570827068a9b0ab138595.83080865`
- ✅ Site ID: `105905542`
- ✅ Secret Key: `176118419568a9b10a66c829.71997677`

### 2. **Support Complet des Méthodes de Paiement**

#### Canaux de Paiement Disponibles
- ✅ **ALL**: Tous les canaux (Mobile Money, Carte Bancaire, Wallet)
- ✅ **MOBILE_MONEY**: Paiement mobile uniquement
- ✅ **CREDIT_CARD**: Carte bancaire uniquement (Visa, Mastercard)
- ✅ **WALLET**: Portefeuille électronique uniquement

#### Configuration
Le canal peut être défini via:
- Variable d'environnement `CINETPAY_CHANNELS` (défaut: "ALL")
- Paramètre `channels` dans la requête d'initialisation

### 3. **Gestion des Montants**

#### Validation des Montants
- ✅ **Multiples de 5**: Les montants sont automatiquement arrondis au multiple de 5 supérieur (sauf USD)
- ✅ **Montants Minimum/Maximum** par devise:
  - XOF: 100 - 2,000,000
  - XAF: 100 - 1,500,000
  - CDF: 100 - 2,000,000
  - GNF: 1,000 - 15,000,000
  - USD: 1 - 3,000 (pas de restriction multiple de 5)

### 4. **Informations Client Obligatoires**

Pour activer l'option **Carte Bancaire**, les informations suivantes sont requises:
- ✅ `customer_name`: Nom du client
- ✅ `customer_surname`: Prénom du client
- ✅ `customer_email`: Email du client
- ✅ `customer_phone_number`: Numéro de téléphone (formaté avec préfixe pays)
- ✅ `customer_address`: Adresse du client
- ✅ `customer_city`: Ville du client
- ✅ `customer_country`: Code pays ISO (2 lettres)
- ✅ `customer_state`: État du pays
- ✅ `customer_zip_code`: Code postal

#### Format du Numéro de Téléphone
- Format automatique avec préfixe pays selon la devise ou le pays fourni
- Support pour `lock_phone_number`: Permet de préfixer le numéro sur le guichet

### 5. **Gestion des Statuts de Transaction**

#### Statuts Supportés
- ✅ **ACCEPTED**: Transaction acceptée
- ✅ **REFUSED**: Transaction refusée
- ✅ **CANCELLED**: Transaction annulée
- ✅ **PENDING**: En attente
- ✅ **WAITING_FOR_CUSTOMER**: En attente de validation client
- ✅ **WAITING_CUSTOMER_TO_VALIDATE**: En attente de validation
- ✅ **WAITING_CUSTOMER_PAYMENT**: En attente de paiement
- ✅ **WAITING_CUSTOMER_OTP_CODE**: En attente du code OTP

### 6. **Gestion des Erreurs**

#### Codes d'Erreur Supportés
- ✅ **00**: SUCCES
- ✅ **201**: CREATED
- ✅ **600**: PAYMENT_FAILED
- ✅ **602**: INSUFFICIENT_BALANCE
- ✅ **604**: OTP_CODE_ERROR
- ✅ **608**: MINIMUM_REQUIRED_FIELDS
- ✅ **606**: INCORRECT_SETTINGS
- ✅ **609**: AUTH_NOT_FOUND
- ✅ **623**: WAITING_CUSTOMER_TO_VALIDATE
- ✅ **624**: PROCESSING_ERROR
- ✅ **625**: ABONNEMENT_OR_TRANSACTIONS_EXPIRED
- ✅ **627**: TRANSACTION_CANCEL
- ✅ **662**: WAITING_CUSTOMER_PAYMENT
- ✅ **663**: WAITING_CUSTOMER_OTP_CODE

### 7. **Webhook de Notification**

#### Validation HMAC
- ✅ Vérification du token HMAC avec la clé secrète
- ✅ Construction de la chaîne selon la documentation CinetPay
- ✅ Algorithme SHA256

#### Paramètres Reçus
- `cpm_site_id`: ID du site
- `cpm_trans_id`: ID de la transaction
- `cpm_trans_date`: Date de la transaction
- `cpm_amount`: Montant
- `cpm_currency`: Devise
- `signature`: Signature
- `payment_method`: Méthode de paiement
- `cel_phone_num`: Numéro de téléphone
- `cpm_phone_prefixe`: Préfixe pays
- `cpm_language`: Langue
- `cpm_version`: Version
- `cpm_payment_config`: Configuration de paiement
- `cpm_page_action`: Action de la page
- `cpm_custom`: Métadonnées personnalisées
- `cpm_designation`: Désignation
- `cpm_error_message`: Message d'erreur

### 8. **Nettoyage des Données**

#### Caractères Spéciaux
- ✅ Suppression des caractères spéciaux non autorisés (#, /, $, _, &)
- ✅ Nettoyage de la description
- ✅ Nettoyage de tous les champs texte
- ✅ Limitation de la longueur des champs

#### Transaction ID
- ✅ Suppression des tirets du UUID
- ✅ Limitation à 25 caractères maximum
- ✅ Validation des caractères spéciaux

### 9. **Support Multi-Devises**

#### Devises Supportées
- ✅ **XOF**: Franc CFA Ouest (Côte d'Ivoire, Sénégal, Togo, Bénin, Mali, Burkina Faso)
- ✅ **XAF**: Franc CFA Centre (Cameroun)
- ✅ **CDF**: Franc Congolais (RD Congo)
- ✅ **GNF**: Franc Guinéen (Guinée)
- ✅ **USD**: Dollar US (RD Congo USD)

#### Mapping Pays/Devises
- Détection automatique du pays selon la devise
- Préfixes téléphoniques automatiques selon le pays

### 10. **Paramètres Optionnels**

#### Langue du Guichet
- ✅ `lang`: "fr" (français) ou "en" (anglais)
- Défaut: "fr"

#### Lock Phone Number
- ✅ `lock_phone_number`: Permet de préfixer le numéro sur le guichet
- Utilisé avec `customer_phone_number`

#### Invoice Data
- ✅ Support pour 3 champs personnalisés dans la facture
- Format: `{"Donnee1": "", "Donnee2": "", "Donnee3": ""}`

## 📋 Utilisation

### Initialisation d'un Paiement

```python
from src.api.payments.schemas import PaymentInitInput

payment_data = PaymentInitInput(
    payable=your_payable_object,
    amount=10000,
    product_currency="XAF",
    description="Paiement formation",
    payment_provider="CINETPAY",
    customer_name="John",
    customer_surname="Doe",
    customer_email="john.doe@example.com",
    customer_phone_number="+237655123456",
    customer_address="Yaoundé",
    customer_city="Yaoundé",
    customer_country="CM",
    customer_state="CM",
    customer_zip_code="065100",
    channels="ALL",  # ou "MOBILE_MONEY", "CREDIT_CARD", "WALLET"
    lock_phone_number=False,
    lang="fr"
)
```

### Vérification du Statut

```python
from src.api.payments.service import CinetPayService

# Version asynchrone
result = await CinetPayService.check_cinetpay_payment_status(transaction_id)

# Version synchrone
result = CinetPayService.check_cinetpay_payment_status_sync(transaction_id)
```

## 🔧 Configuration

### Variables d'Environnement

```env
CINETPAY_API_KEY=42570827068a9b0ab138595.83080865
CINETPAY_SITE_ID=105905542
CINETPAY_SECRET_KEY=176118419568a9b10a66c829.71997677
CINETPAY_NOTIFY_URL=https://votre-domaine.com/api/v1/payments/cinetpay/notify
CINETPAY_RETURN_URL=https://votre-domaine.com
CINETPAY_CURRENCY=XAF
CINETPAY_CHANNELS=ALL
```

## 📝 Notes Importantes

1. **Transaction ID**: Ne doit pas contenir de caractères spéciaux (#, /, $, _, &)
2. **Description**: Ne doit pas contenir de caractères spéciaux
3. **Montants**: Doivent être des multiples de 5 (sauf USD)
4. **Carte Bancaire**: Nécessite toutes les informations client
5. **Webhook**: Doit retourner 200 OK pour être considéré comme valide
6. **HMAC**: La validation est obligatoire en production

## 🐛 Dépannage

### Erreur 608: MINIMUM_REQUIRED_FIELDS
- Vérifier que tous les champs obligatoires sont fournis
- Vérifier le format JSON de la requête

### Erreur 609: AUTH_NOT_FOUND
- Vérifier que l'API Key est correcte
- Vérifier dans le back-office CinetPay

### Erreur 613: ERROR_SITE_ID_NOTVALID
- Vérifier que le Site ID est correct
- Vérifier dans le back-office CinetPay

### Erreur 624: PROCESSING_ERROR
- Vérifier que l'API Key est correcte
- Vérifier que `lock_phone_number` est False si `customer_phone_number` est incorrect

### Erreur 403: Accès Interdit
- Vérifier que le service est identifié dans le back-office
- Vérifier que les URLs de notification et retour ne sont pas en localhost

## 📚 Références

- Documentation CinetPay: https://docs.cinetpay.com
- API Endpoint: https://api-checkout.cinetpay.com/v2/payment
- API Check: https://api-checkout.cinetpay.com/v2/payment/check

