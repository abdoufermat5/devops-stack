# DevOps Stack - Shopping List API

A FastAPI-based Shopping List application with full DevOps tooling including Docker, Kubernetes (Helm), and ArgoCD support.

## Project Structure

```
├── app/                    # FastAPI application
│   ├── main.py             # Application entry point
│   ├── db.py               # Database configuration
│   ├── models/             # SQLAlchemy models
│   ├── routers/            # API route handlers
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   ├── utils/              # Utility functions
│   ├── Dockerfile          # Docker image definition
│   └── docker-compose.yml  # Local development setup
└── helm/                   # Kubernetes Helm charts
    └── shopping-api/       # Shopping API Helm chart
```

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16
- **Containerization**: Docker
- **Orchestration**: Kubernetes with Helm
- **CI/CD**: ArgoCD ready

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| POST | `/products` | Create a product |
| GET | `/products` | List products (filter by category, bought status) |
| GET | `/products/{id}` | Get product by ID |
| PATCH | `/products/{id}` | Update product |
| DELETE | `/products/{id}` | Delete product |
| POST | `/products/{id}/favorite` | Add to favorites |
| DELETE | `/products/{id}/favorite` | Remove from favorites |
| POST | `/products/from-favorites` | Add products from favorites |
| GET | `/products/categories` | List available categories |
| GET | `/products/favorites` | List favorites |
| GET | `/products/history` | List history |

Interactive API docs available at `/docs` when running.

## Getting Started

### Local Development with Docker Compose

```bash
cd app
docker-compose up --build
```

The API will be available at `http://localhost:8000`

### Building Docker Image

```bash
cd app
docker build -t shopping-api:latest .
```

## Kubernetes Deployment

### Install with Helm

```bash
helm install shopping-api ./helm/shopping-api
```

### Configuration

Key values in `helm/shopping-api/values.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image.repository` | `localhost:5000/shopping-api` | Docker image |
| `image.tag` | `latest` | Image tag |
| `replicaCount` | `2` | Number of pods |
| `service.type` | `NodePort` | Service type |
| `service.nodePort` | `30800` | External port |
| `database.host` | `shopping-db-postgresql` | PostgreSQL host |

### Monitoring

Prometheus monitoring is enabled by default. Metrics are exposed at `/metrics`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg2://shopping:shopping@localhost:5432/shopping_db` | Database connection string |
