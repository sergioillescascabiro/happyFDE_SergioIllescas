# Deployment Guide — HappyFDE

This document provides instructions on how to containerize and deploy the HappyFDE platform to a production environment on Google Cloud Platform (GCP).

## 🐳 Containerization

The solution consists of two primary services:
1. **API Backend**: Built using a multi-stage Dockerfile optimized for Python performance.
2. **Frontend Dashboard**: Served via Nginx after a static build phase.

## ☁️ Infrastructure Setup (GCP)

To ensure high availability and data persistence, we recommend:
- **Cloud Run**: For stateless application scaling.
- **Cloud SQL (PostgreSQL)**: For managed database reliability.
- **Artifact Registry**: To manage versioned container images.

> [!NOTE]  
> Detailed Terraform instructions and shell scripts will be provided in the next phase of development.

## 🛠️ Reproduction Steps

1. **Build Images**:
   ```bash
   docker build -t gcr.io/[PROJECT_ID]/api ./backend
   docker build -t gcr.io/[PROJECT_ID]/front ./frontend
   ```
2. **Push to Registry**:
   ```bash
   docker push gcr.io/[PROJECT_ID]/api
   docker push gcr.io/[PROJECT_ID]/front
   ```
3. **Provision Resources**: Apply the terraform configuration found in `/terraform`.
