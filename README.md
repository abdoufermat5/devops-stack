# Shopping List API

API REST construite avec FastAPI et PostgreSQL pour gérer une liste de courses. Déployée sur Kubernetes (k3s) via un pipeline GitOps complet : Gitea → Gitea Actions → ArgoCD → k3s.

![Architecture](stack.svg)

---


## Prérequis — environnement de lab
 
Ce lab a été réalisé sur une VM Ubuntu Desktop importée depuis [osboxes.org](https://www.osboxes.org/ubuntu/) (OVA Ubuntu 24.04) et lancée sur **VMware Workstation**.
 
### Configuration VM recommandée
 
| Ressource | Minimum | Recommandé | Lab utilisé |
|---|---|---|---|
| CPU | 2 vCPU | 4 vCPU | 4 vCPU |
| RAM | 6 Go | 8 Go | 8 Go |
| Stockage | 30 Go | 50 Go | 50 Go |
| Réseau | NAT | NAT ou Bridged | NAT |
 
> Avec moins de 6 Go de RAM, les pods Prometheus + Grafana peuvent être en `OOMKilled`. Si les ressources sont limitées, garder le namespace `monitoring` scalé à 0 et ne le démarrer qu'au moment des tests.
 
### Logiciels requis sur la VM
 
```bash
# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # puis se reconnecter
 
# Git
sudo apt-get install -y git
 
# curl, jq (utilisés dans les commandes de ce README)
sudo apt-get install -y curl jq
```
 
### Importer l'OVA sur VMware Workstation
 
```
1. Télécharge l'OVA Ubuntu 24.04 sur https://www.osboxes.org/ubuntu/
2. VMware Workstation → File → Open → sélectionne le fichier .ova
3. Ajuste les ressources (CPU / RAM / Disk) avant de démarrer
4. Démarre la VM — login : osboxes / mot de passe : osboxes.org
```

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
├── runner/                         ← configuration du runner Gitea Actions
│   ├── install-runner.sh           ← script d'installation automatisé
│   ├── act-runner.service          ← service systemd (démarrage au boot)
│   └── README.md                   ← documentation du runner
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

### Installation du runner CI

Le runner (`act_runner`) doit être installé une seule fois sur la VM host. Il tourne directement sur le host — pas dans un container — pour avoir accès au daemon Docker local et pouvoir builder des images.

**1. Récupère le token d'enregistrement sur Gitea :**

```
http://<GITEA_IP>:30300/<user>/<repo>/settings/actions/runners
→ "Create new runner" → copie le token affiché
```

**2. Lance le script d'installation :**

```bash
chmod +x runner/install-runner.sh
./runner/install-runner.sh <GITEA_IP> <TOKEN>

# Exemple :
./runner/install-runner.sh 192.168.1.100 ClOEHoZ1PAJHFNvR...
```

Le script télécharge le binaire `act_runner`, l'enregistre sur Gitea avec le label `ubuntu-latest:host` et installe un service systemd pour le démarrer automatiquement au boot.

**3. Vérifie que le runner est actif :**

```bash
sudo systemctl status act-runner
```

Puis sur Gitea : `http://<GITEA_IP>:30300/<user>/<repo>/settings/actions/runners` — `local-runner` doit apparaître avec un point vert.

**Commandes utiles :**

```bash
sudo journalctl -u act-runner -f    # logs en temps réel
sudo systemctl restart act-runner   # redémarrer
sudo systemctl stop act-runner      # arrêter (désactive le CI)
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

## Installation de l'infrastructure

Cette section couvre l'installation complète du stack de zéro sur une VM Linux (Ubuntu 24).

### 1. k3s

```bash
curl -sfL https://get.k3s.io | sh -

# Configure kubectl sans sudo
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config

# Vérifie
kubectl get nodes   # doit afficher le nœud en Ready
```

### 2. Helm

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Ajoute les repos utilisés
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add gitea-charts https://dl.gitea.com/charts/
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### 3. Registry Docker local

k3s a besoin d'un registry accessible pour puller les images buildées par le CI.

```bash
# Lance le registry
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# Configure k3s pour faire confiance à ce registry (HTTP)
sudo mkdir -p /etc/rancher/k3s
sudo tee /etc/rancher/k3s/registries.yaml <<EOF
mirrors:
  "localhost:5000":
    endpoint:
      - "http://localhost:5000"
EOF

sudo systemctl restart k3s
```

### 4. Gitea

```bash
helm install gitea gitea-charts/gitea \
  --set service.http.type=NodePort \
  --set service.http.nodePort=30300

# Attends que les pods soient Running
kubectl get pods -l app.kubernetes.io/name=gitea -w
```

Accès : `http://localhost:30300` — crée un compte admin, puis un repo `devops-stack`.

Clone et pousse le contenu de ce repo :

```bash
git remote set-url origin http://localhost:30300/<user>/devops-stack.git
git push -u origin main
```

### 5. PostgreSQL

```bash
helm install shopping-db bitnami/postgresql \
  --set auth.username=shopping \
  --set auth.password=shopping \
  --set auth.database=shopping_db

# Vérifie
kubectl get pods -l app.kubernetes.io/name=postgresql -w
```

Le Service créé s'appelle `shopping-db-postgresql` — c'est le hostname utilisé dans `DATABASE_URL`.

### 6. ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Expose l'UI en NodePort
kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "NodePort", "ports": [{"port": 443, "nodePort": 30443, "targetPort": 8080}]}}'

# Récupère le mot de passe admin
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d && echo

# Attends que tous les pods ArgoCD soient Running
kubectl get pods -n argocd -w
```

Accès UI : `https://localhost:30443` (login : `admin`).

Crée le projet par défaut et déploie l'application :

```bash
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: default
  namespace: argocd
spec:
  sourceRepos: ['*']
  destinations:
    - namespace: '*'
      server: '*'
  clusterResourceWhitelist:
    - group: '*'
      kind: '*'
EOF

# Adapte le repoURL avec l'IP de ta VM
kubectl apply -f argocd/application.yaml
```

### 7. Runner CI (Gitea Actions)

Voir la section [Installation du runner CI](#installation-du-runner-ci) ci-dessus.

### 8. Prometheus + Grafana

```bash
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=30900 \
  --set prometheus.service.type=NodePort \
  --set prometheus.service.nodePort=30090 \
  --set alertmanager.enabled=false

# Attends que tous les pods soient Running (~2-3 min)
kubectl get pods -n monitoring -w
```

Applique le ServiceMonitor pour scraper l'API :

```bash
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: shopping-api
  namespace: monitoring
  labels:
    release: monitoring
spec:
  namespaceSelector:
    matchNames:
      - default
  selector:
    matchLabels:
      app: shopping-api
  endpoints:
    - port: "http"
      path: /metrics
      interval: 15s
EOF
```

Récupère le mot de passe Grafana :

```bash
kubectl get secret monitoring-grafana -n monitoring \
  -o jsonpath="{.data.admin-password}" | base64 -d && echo
```

Accès Grafana : `http://localhost:30900` (login : `admin`).

### 9. k6

```bash
sudo gpg --no-default-keyring \
  --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69

echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list

sudo apt-get update && sudo apt-get install k6 -y
```

---

## Déploiement Kubernetes

### Prérequis

- Tous les composants de la section précédente installés
- Registry local sur `localhost:5000`
- Gitea sur `http://localhost:30300`
- ArgoCD sur `https://localhost:30443`
- Runner CI actif (`sudo systemctl status act-runner`)

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