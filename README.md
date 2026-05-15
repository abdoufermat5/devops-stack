# Shopping List API

![Architecture](stack.svg)

API REST construite avec FastAPI et PostgreSQL pour gérer une liste de courses. Déployée sur Kubernetes (k3s) via un pipeline GitOps complet : Gitea → Gitea Actions → ArgoCD → k3s.

---

## Stack technique

| Couche | Technologie |
|---|---|
| API | FastAPI (Python 3.12) |
| Base de données | PostgreSQL 16 |
| ORM | SQLAlchemy |
| Serveur ASGI | Uvicorn |
| Conteneurisation | Docker |
| Orchestration | k3s (Kubernetes) |
| Packaging K8s | Helm |
| GitOps / CD | ArgoCD |
| CI | Gitea Actions |
| Monitoring | Prometheus + Grafana |
| Tests de charge | k6 |

---

## Structure du projet

```
devops-stack/
├── app/                            ← code source de l'API
│   ├── main.py                     ← point d'entrée FastAPI + exposition /metrics
│   ├── db.py                       ← config SQLAlchemy (pool de connexions)
│   ├── Dockerfile                  ← image de production
│   ├── docker-compose.yml          ← dev local avec PostgreSQL
│   ├── requirements.txt
│   ├── models/
│   │   └── item.py                 ← modèle SQLAlchemy (table products)
│   ├── schemas/
│   │   └── item.py                 ← schémas Pydantic (validation entrée/sortie)
│   ├── routers/
│   │   └── items.py                ← endpoints /products
│   ├── services/
│   │   └── shopping_service.py     ← logique métier
│   └── utils/
├── helm/
│   └── shopping-api/               ← Helm chart de l'application
│       ├── Chart.yaml
│       ├── values.yaml             ← config (image tag, replicas, ressources...)
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           ├── middleware.yaml     ← Traefik StripPrefix /api
│           └── secret.yaml        ← DATABASE_URL injectée via K8s Secret
├── argocd/
│   └── application.yaml            ← manifeste ArgoCD (source Gitea → cluster)
├── k6/
│   └── shopping-api-test.js        ← scénario de test de charge
└── .gitea/
    └── workflows/
        └── ci.yaml                 ← pipeline CI (build → push → deploy)
```

---

## Endpoints

| Méthode | URL | Description |
|---|---|---|
| `GET` | `/` | Healthcheck |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/metrics` | Métriques Prometheus |
| `POST` | `/products` | Créer un produit |
| `GET` | `/products` | Lister les produits (filtres : `category`, `bought`) |
| `GET` | `/products/{id}` | Récupérer un produit |
| `PATCH` | `/products/{id}` | Modifier un produit (quantité, acheté) |
| `DELETE` | `/products/{id}` | Supprimer un produit |
| `POST` | `/products/{id}/favorite` | Ajouter aux favoris |
| `DELETE` | `/products/{id}/favorite` | Retirer des favoris |
| `POST` | `/products/from-favorites` | Ajouter les favoris à la liste |
| `GET` | `/products/favorites` | Lister les favoris |
| `GET` | `/products/history` | Historique des achats |
| `GET` | `/products/categories` | Lister les catégories disponibles |

---

## Lancer en local (Docker Compose)

```bash
cd app/
docker compose up --build
```

L'API est disponible sur `http://localhost:8000`.
Swagger UI sur `http://localhost:8000/docs`.

Variables d'environnement utilisées :

| Variable | Valeur par défaut | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://shopping:shopping@localhost:5432/shopping_db` | URL de connexion PostgreSQL |
| `PYTHONUNBUFFERED` | `1` | Logs Python non bufférisés |

---

## Pipeline CI/CD

### Schéma du flux

```
git push app/**
       │
       ▼
   Gitea (repo)
       │  déclenche
       ▼
Gitea Actions (runner local)
       │
       ├─ docker build -t localhost:5000/shopping-api:{tag}
       ├─ docker push localhost:5000/shopping-api:{tag}
       ├─ sed values.yaml → tag: "{tag}"
       └─ git commit + push
                │
                ▼
           ArgoCD détecte le changement dans values.yaml
                │
                ▼
        kubectl apply (RollingUpdate — zéro downtime)
```

### Déclencher le CI

Le CI se déclenche automatiquement sur tout push sur `main` qui modifie un fichier sous `app/`. Les commits qui touchent uniquement `helm/` sont ignorés (ce sont les commits automatiques du CI lui-même — évite la boucle infinie).

```bash
# Exemple : modifier l'app et pousser
vim app/main.py
git add app/
git commit -m "feat: ma modification"
git push
```

Suivre l'exécution : `http://localhost:30300/asadiakhou/devops-stack/actions`

---

## Déploiement Kubernetes

### Prérequis

- k3s installé et running
- Registry local sur `localhost:5000`
- Gitea sur `http://localhost:30300`
- ArgoCD sur `https://localhost:30443`

### Commandes utiles

```bash
# État de l'application ArgoCD
kubectl get application shopping-api -n argocd

# Pods de l'app
kubectl get pods -l app=shopping-api

# Logs en temps réel
kubectl logs -l app=shopping-api -f

# Forcer une resynchronisation ArgoCD
kubectl patch application shopping-api -n argocd \
  --type merge -p '{"operation":{"sync":{"revision":"HEAD"}}}'

# Rollback : changer le tag dans values.yaml et pousser
vim helm/shopping-api/values.yaml   # modifier image.tag
git add helm/shopping-api/values.yaml
git commit -m "revert: rollback vers <ancien-tag>"
git push
```

### Accès à l'API en cluster

| Accès | URL |
|---|---|
| NodePort direct | `http://localhost:30800` |
| Via Ingress Traefik | `http://localhost/api/products` |
| Swagger UI | `http://localhost/docs` |

---

## Tests de charge (k6)

```bash
# Lancer le test complet (4 stages, jusqu'à 50 VUs)
k6 run k6/shopping-api-test.js
```

Le scénario simule un cycle utilisateur complet : liste → création → lecture → patch → suppression.

Seuils définis :

| Métrique | Seuil |
|---|---|
| `http_req_duration` p(95) | < 1500ms |
| `duration_create_product` p(95) | < 2000ms |
| `http_req_failed` | < 1% |

---

## Monitoring

```bash
# Démarrer Prometheus + Grafana (si scaled down)
kubectl scale deployment --all -n monitoring --replicas=1
kubectl scale statefulset --all -n monitoring --replicas=1

# Accès Grafana
http://localhost:30900   # admin / <mot de passe dans le secret>

# Récupérer le mot de passe Grafana
kubectl get secret monitoring-grafana -n monitoring \
  -o jsonpath="{.data.admin-password}" | base64 -d
```

Queries Prometheus utiles :

```promql
# Taux de requêtes par endpoint
rate(http_requests_total{job="shopping-api"}[1m])

# Latence p95
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket{job="shopping-api"}[1m])
)

# Taux d'erreurs 5xx
rate(http_requests_total{job="shopping-api", status_code=~"5.."}[1m])
```

Dashboard Grafana importé : ID `17175`

---

## Configuration du pool de connexions

Le fichier `db.py` configure SQLAlchemy avec un pool dimensionné pour tenir sous charge :

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,       # connexions permanentes
    max_overflow=10,    # connexions bonus en pic
    pool_timeout=30,    # timeout d'attente
    pool_pre_ping=True, # vérifie les connexions avant usage
)
```

Sans ce pool, à 50 VUs simultanés la latence p95 dépasse 1.5s. Avec, elle reste sous 500ms en conditions normales.
