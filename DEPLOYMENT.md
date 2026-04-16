# Deployment Guide — HappyFDE

Full deployment to Google Cloud Platform using Docker + Terraform.

## Prerequisites

| Tool | Version | Purpose |
| ---- | ------- | ------- |
| [Terraform](https://developer.hashicorp.com/terraform/install) | >= 1.0 | Infrastructure provisioning |
| [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) | latest | GCP authentication |
| [Docker](https://docs.docker.com/get-docker/) | latest | Image build & push |
| [uv](https://github.com/astral-sh/uv) | latest | Python dependency management |

A GCP project with **billing enabled** is required.

---

## 1. Authenticate to GCP

```bash
gcloud auth application-default login
gcloud config set project YOUR_GCP_PROJECT_ID
```

---

## 2. Provision Infrastructure (Terraform)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id, db_password, agent_api_key, dashboard_token
```

```bash
terraform init
terraform plan
terraform apply
```

This creates:

- **VPC network** with private peering for Cloud SQL
- **Cloud SQL** — PostgreSQL 16 on private network
- **Artifact Registry** — Docker image repository
- **Secret Manager** — stores agent key and dashboard token
- **Cloud Run** — backend (port 8000) and frontend (port 3000)

After `apply`, note the output URLs:

```text
backend_url  = "https://happyfde-api-xxxx-uc.a.run.app"
frontend_url = "https://happyfde-dashboard-xxxx-uc.a.run.app"
```

---

## 3. Build and Push Docker Images

Replace `REGION` and `PROJECT_ID` with your values (must match `terraform.tfvars`).

```bash
# Authenticate Docker to Artifact Registry
gcloud auth configure-docker REGION-docker.pkg.dev

# Backend
docker build -t REGION-docker.pkg.dev/PROJECT_ID/happyfde-repo/backend:latest ./backend
docker push REGION-docker.pkg.dev/PROJECT_ID/happyfde-repo/backend:latest

# Frontend
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://happyfde-api-xxxx-uc.a.run.app \
  -t REGION-docker.pkg.dev/PROJECT_ID/happyfde-repo/frontend:latest ./frontend
docker push REGION-docker.pkg.dev/PROJECT_ID/happyfde-repo/frontend:latest
```

> The frontend build arg `NEXT_PUBLIC_API_URL` must point to the backend Cloud Run URL from step 2.

---

## 4. Redeploy Cloud Run with the new images

```bash
gcloud run deploy happyfde-api \
  --image REGION-docker.pkg.dev/PROJECT_ID/happyfde-repo/backend:latest \
  --region REGION

gcloud run deploy happyfde-dashboard \
  --image REGION-docker.pkg.dev/PROJECT_ID/happyfde-repo/frontend:latest \
  --region REGION
```

---

## 5. Seed the database (first deploy only)

```bash
# Connect via Cloud SQL Auth Proxy (or from a Cloud Run job)
cd backend
DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/happyrobot" \
  uv run alembic upgrade head

DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/happyrobot" \
  uv run python -m app.seed
```

---

## Local development (without GCP)

For local development, Docker Compose spins up the full stack without any cloud dependencies:

```bash
docker compose up --build
# API       → http://localhost:8000
# Dashboard → http://localhost:3000
```

See [README.md](./README.md) for the manual local setup without Docker.
