# Commande de Déploiement

## Commande Correcte

```bash
sudo docker compose up -d --build
```

## Explication

- `up` : Crée et démarre les containers
- `-d` : Mode détaché (en arrière-plan)
- `--build` : Reconstruit les images avant de démarrer

## Séquence Complète

```bash
cd /opt/lfm-back/
sudo docker compose down
sudo docker compose up -d --build
```

