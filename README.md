# HappyFDE — Freight Decision Engine (Acme Logistics)

HappyFDE is a production-ready freight brokerage platform designed to automate carrier negotiations and provide real-time executive visibility into logistics operations.

## 🏗️ Technical Architecture

The platform is built on a modern, decoupled stack designed for high availability and security:

*   **Backend**: Python 3.12 (FastAPI) with SQLAlchemy 2.0.
*   **Frontend**: Next.js 14+ (React) with Vanilla CSS and high-density data visualizations.
*   **Database**: PostgreSQL 16 (Google Cloud SQL) on a private network via VPC Peering.
*   **Infrastructure**: Fully governed by **Terraform** (IaC).
*   **Deployment**: Serverless on **Google Cloud Run** using Artifact Registry.

## 🌟 Key Features

### 1. AI Negotiation Engine (Paul)
Automated negotiation logic that handles carrier offers, computes margins in real-time, and makes intelligent counter-offers based on target spreads and historical data.

### 2. Executive Pulsation Dashboard
A high-fidelity interface designed for data-driven decisions:
*   **Carrier Outcome Analysis**: Real-time distribution of wins vs losses.
*   **Margin Tracking**: Instant visibility into operational profitability.
*   **Live Communication Feed**: Full audit trail of AI-carrier interactions.

## 🚀 Getting Started

### Local Setup (Development)

Ensure you have **Docker** and **uv** (for Python) installed.

1.  **Infrastructure**:
    ```bash
    docker run -d --name happyfde-db -p 5433:5432 -e POSTGRES_DB=happyrobot -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres postgres:16-alpine
    ```

2.  **Backend**:
    ```bash
    cd backend
    uv sync
    uv run python -m app.seed  # Populate local DB with standard load data
    uv run uvicorn app.main:app --reload
    ```

3.  **Frontend**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## 🔐 Security & Operations

*   **Secret Management**: Production secrets are managed via Google Secret Manager.
*   **Private Networking**: The database is inaccessible from the public internet, using Google's Service Networking for internal communication.
*   **Observability**: Integrated with Google Cloud Logging for real-time traffic analysis.

---
Developed for **Acme Logistics** technical challenge.
