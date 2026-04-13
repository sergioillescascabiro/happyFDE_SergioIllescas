# HappyFDE — Freight Brokerage Operations Platform

Full-stack platform for the HappyRobot FDE Technical Challenge.

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker
- uv (Python package manager): `pip install uv`

### Database
```bash
docker run -d --name happyfde-db -p 5433:5432 -e POSTGRES_DB=happyrobot -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres postgres:16-alpine
```

### Backend
```bash
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
