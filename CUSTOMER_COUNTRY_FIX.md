# Correction : customer_country doit être "CM"

## Problème Identifié

L'erreur 500 sur le guichet CinetPay était causée par une valeur incorrecte de `customer_country`. 

**Pour votre compte CinetPay, `customer_country` doit toujours être "CM" (Cameroun).**

## Correction Appliquée

### 1. **customer_country Toujours "CM"**

Le code a été modifié pour que `customer_country` soit **toujours "CM"** pour ce compte CinetPay :

```python
# AVANT (incorrect)
if payment_data.customer_country:
    payload["customer_country"] = country_mapping.get(country_code, "CM")
else:
    payload["customer_country"] = currency_to_country.get(payment_data.currency, "CM")

# APRÈS (correct)
payload["customer_country"] = "CM"  # Toujours "CM" pour ce compte CinetPay
```

### 2. **customer_state Toujours "CM"**

Puisque `customer_state` doit correspondre au code pays, il est aussi défini à "CM" :

```python
payload["customer_state"] = "CM"  # Toujours "CM" pour ce compte
```

### 3. **Préfixe Téléphonique Toujours "237"**

Le préfixe téléphonique est maintenant toujours "237" (Cameroun) :

```python
country_prefix = "237"  # Cameroun (toujours pour ce compte)
```

## ✅ Résultat

Maintenant, **tous les paiements** (Mobile Money, Carte Bancaire, Wallet) auront :
- ✅ `customer_country` = "CM"
- ✅ `customer_state` = "CM"
- ✅ Préfixe téléphonique = "237"

## 📋 Payload Final

```python
{
    "customer_country": "CM",  # ✅ Toujours "CM"
    "customer_state": "CM",    # ✅ Toujours "CM"
    "customer_phone_number": "+237657807309",  # ✅ Préfixe "237"
    # ... autres champs
}
```

## 🚀 Test

Vous pouvez maintenant tester un paiement Mobile Money. Le problème de l'erreur 500 devrait être résolu car `customer_country` est maintenant toujours "CM" comme requis par votre compte CinetPay.

