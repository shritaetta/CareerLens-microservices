# CareerLens Kubernetes (K8s) Deployment Guide

This directory contains the Kubernetes manifests for CareerLens structured using **Kustomize** (`base/` plus `overlays/dev/`), specifically tailored for local development on a **kind** (Kubernetes in Docker) cluster.

---

## Architecture Overview

```
k8s/
├── kind-cluster.yaml          # Kind cluster config (ingress-ready with host port 80/443 mappings)
├── base/                      # Production-grade base declarations
│   ├── kustomization.yaml
│   ├── configmap.yaml         # Non-secret application configurations
│   ├── postgres-configmap.yaml# DB schema initialization script (CREATE DATABASE auth_db, profile_db)
│   ├── postgres-statefulset.yaml # Dev PostgreSQL 16 StatefulSet with PVC
│   ├── postgres-service.yaml  # ClusterIP service for postgres:5432
│   ├── redis-deployment.yaml  # Dev Redis 7 Deployment
│   ├── redis-service.yaml     # ClusterIP service for redis:6379
│   ├── auth-deployment.yaml   # Auth microservice Deployment (port 8000)
│   ├── auth-service.yaml      # ClusterIP service for auth:8000
│   ├── profile-deployment.yaml# Profile microservice Deployment (port 8000)
│   ├── profile-service.yaml   # ClusterIP service for profile:8000
│   ├── files-pvc.yaml         # PVC for file uploads (storage for dev)
│   ├── files-deployment.yaml  # Files microservice Deployment (port 8000)
│   ├── files-service.yaml     # ClusterIP service for files:8000
│   ├── ml-pvc.yaml            # PVC for ML recommendation dataset
│   ├── ml-dataset-seed.yaml   # ConfigMap seeding Book2.xlsx into ML PVC
│   ├── ml-deployment.yaml     # ML microservice Deployment (cpu 500m/mem 1Gi req, 2Gi limit, startupProbe)
│   ├── ml-service.yaml        # ClusterIP service for ml:8000
│   ├── ml-hpa.yaml            # HorizontalPodAutoscaler for ML (2 to 6 replicas at 70% CPU)
│   ├── frontend-deployment.yaml # React frontend Deployment (port 80)
│   ├── frontend-service.yaml  # ClusterIP service for frontend:80
│   └── ingress.yaml           # Nginx Ingress routes mirroring API gateway routing rules
└── overlays/
    └── dev/                   # Dev overlay targeting local kind cluster
        └── kustomization.yaml # Injects dev Secret from literals & replaces image placeholders
```

---

## Important Production Notes

> [!IMPORTANT]
> **Dev vs. Production Deployments:**
> 1. **Postgres & Redis:** The PostgreSQL StatefulSet and Redis Deployment included in these manifests are intended **strictly for local development and smoke testing**. In production, replace them with managed cloud database solutions such as:
>    - **AWS RDS PostgreSQL** / **Google Cloud SQL** / **Azure Database for PostgreSQL**
>    - **AWS ElastiCache for Redis** / **Google Cloud Memorystore** / **Azure Cache for Redis**
> 2. **File Storage:** The `files-uploads-pvc` PVC provides local node volume storage for development. In production, configure object storage like **AWS S3**, **MinIO**, or **Google Cloud Storage**.
> 3. **Secrets Management:** The `careerlens-secrets` Secret in `overlays/dev` is generated from non-production literals. In production, do not commit raw secrets; use **External Secrets Operator**, **AWS Secrets Manager**, **HashiCorp Vault**, or **Sealed Secrets**.
> 4. **ML Dataset:** The ML dataset PVC is automatically seeded via an init container for standalone local operation. In production, large models and datasets should be hosted in object storage (S3) or mounted via high-performance shared filesystems (e.g. AWS EFS / FSx).

---

## Step-by-Step Local Deployment Guide

### Prerequisites
- [Docker Desktop](https://www.docker.com/) running
- [kind](https://kind.sigs.k8s.io/) installed (`kind version`)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed (`kubectl version --client`)

---

### Step 1: Create the Kind Cluster

Create the kind cluster using the ingress-ready configuration:

```bash
kind create cluster --config k8s/kind-cluster.yaml
```

Verify that the node is ready:
```bash
kubectl get nodes
```

---

### Step 2: Install the NGINX Ingress Controller

Deploy the official NGINX Ingress Controller configured for kind:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

Wait until the ingress controller pod is running and ready:
```bash
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=180s
```

---

### Step 3: Build Container Images

Build the local microservice images from the repository root:

```bash
# Build Auth service
docker build -t careerlens-auth:latest ./services/auth

# Build Profile service
docker build -t careerlens-profile:latest ./services/profile

# Build Files service
docker build -t careerlens-files:latest ./services/files

# Build ML service
docker build -t careerlens-ml:latest ./services/ml

# Build Frontend
docker build -t careerlens-frontend:latest ./frontend
```

---

### Step 4: Load Images into the Kind Cluster

Load the built Docker images directly into the kind cluster (so the cluster does not pull from Docker Hub):

```bash
kind load docker-image careerlens-auth:latest --name careerlens-cluster
kind load docker-image careerlens-profile:latest --name careerlens-cluster
kind load docker-image careerlens-files:latest --name careerlens-cluster
kind load docker-image careerlens-ml:latest --name careerlens-cluster
kind load docker-image careerlens-frontend:latest --name careerlens-cluster
```

---

### Step 5: Validate Manifests with Dry-Run

Verify the Kustomize dev overlay manifests against the Kubernetes API server using `--dry-run=server`:

```bash
kubectl apply -k k8s/overlays/dev --dry-run=server
```

---

### Step 6: Deploy to Kind

Apply the manifests using Kustomize:

```bash
kubectl apply -k k8s/overlays/dev
```

Wait for the deployments and statefulsets to complete rollout:

```bash
kubectl rollout status statefulset/postgres --timeout=120s
kubectl rollout status deployment/redis --timeout=120s
kubectl rollout status deployment/auth --timeout=120s
kubectl rollout status deployment/profile --timeout=120s
kubectl rollout status deployment/files --timeout=120s
kubectl rollout status deployment/ml --timeout=300s
kubectl rollout status deployment/frontend --timeout=120s
```

Verify all pods and services:
```bash
kubectl get pods -o wide
kubectl get svc
kubectl get ingress
```

---

### Step 7: Accessing the Application

Because `kind-cluster.yaml` maps container port 80 to host port 80, the Ingress is accessible directly at:

```
http://localhost
```

#### Optional: Port-Forwarding (if host port 80 is occupied)
If port 80 is occupied by another service on your machine, you can port-forward the NGINX Ingress Controller:

```bash
kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80
```
Then access the stack at `http://localhost:8080`.

---

### Step 8: Run Smoke Tests Against the Ingress

Run the smoke test script against the Kubernetes Ingress:

```bash
# Using bash (with SKIP_COMPOSE=true to target Kubernetes instead of docker-compose)
SKIP_COMPOSE=true GATEWAY_URL="http://localhost" ./scripts/smoke.sh

# Or using Python:
$env:SKIP_COMPOSE="true"; $env:GATEWAY_URL="http://localhost"; python scripts/smoke.py
```

All 5 smoke test steps will verify:
1. Health checks on `/gateway-health`, `/api/auth/health`, `/api/profile/health`, `/api/files/health`, and `/api/ml/health`.
2. User registration (`POST /api/auth/signup`).
3. User authentication (`POST /api/auth/login`) and JWT retrieval.
4. User profile persistence (`POST /api/profile/{user_id}`).
5. ML career recommendations (`POST /api/ml/recommend`).

---

### Tear Down Cluster

When done, delete the local kind cluster:
```bash
kind delete cluster --name careerlens-cluster
```
