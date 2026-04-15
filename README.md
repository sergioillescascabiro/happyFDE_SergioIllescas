# HappyFDE — Developer Guide (Engineering Branch)

Welcome to the **Development** branch. This branch is optimized for high-velocity iteration using industry-standard hybrid development patterns.

## 🛠️ Local Development Environment

We use a decoupled architecture where parts of the stack can run locally or point to remote infrastructure.

### 1. The Database (Dockerized)

Instead of installing PostgreSQL natively, we run it in a container.

```bash
docker run -d \
  --name happyfde-db \
  -p 5433:5432 \
  -e POSTGRES_DB=happyrobot \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  postgres:16-alpine
```

### 2. Hybrid Development Modes

Configure your environment by copying `.env.example` in both folders.

#### Mode A: Full Local (Backend + Frontend)

- **Use case:** Working on end-to-end features or database schema changes.
- **Setup:** Both apps point to `localhost`.

#### Mode B: Frontend Only (Remote API)

- **Use case:** Working exclusively on UI/UX improvements without running the backend.
- **Setup:** Change `frontend/.env` to point to the production API URL.

#### Mode C: Backend Only (Remote DB)

- **Use case:** Testing production data locally or debugging cloud-specific issues.
- **Setup:** Change `backend/.env` to point to the Cloud SQL instance (requires auth).

---

## 🚀 Execution Commands

### Backend (Python/FastAPI)

Using `uv` for ultra-fast dependency management.

```bash
cd backend
uv sync
uv run python -m app.seed  # Re-seed with fresh industry-standard data
uv run uvicorn app.main:app --reload
```

### Frontend (Vite/React)

```bash
cd frontend
npm install
npm run dev
```

## 🧪 Testing

Run the comprehensive test suite to ensure no regressions in negotiation logic.

```bash
cd backend
uv run pytest
```
