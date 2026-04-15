# Service Account for the Backend API
resource "google_service_account" "api_sa" {
  account_id   = "happyfde-api-sa"
  display_name = "HappyFDE Backend Service Account"
}

# Grant Secret Manager Access to the SA
resource "google_secret_manager_secret_iam_member" "agent_key_access" {
  secret_id = google_secret_manager_secret.agent_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "dashboard_token_access" {
  secret_id = google_secret_manager_secret.dashboard_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_sa.email}"
}

# Backend Service
resource "google_cloud_run_v2_service" "backend" {
  name     = "happyfde-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api_sa.email
    
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/backend:latest"
      
      ports {
        container_port = 8000
      }

      env {
        name  = "DATABASE_URL"
        value = "postgresql://postgres:${var.db_password}@${google_sql_database_instance.instance.private_ip_address}:5432/happyrobot"
      }

      env {
        name = "AGENT_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.agent_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "DASHBOARD_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.dashboard_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "FMCSA_MOCK"
        value = "false"
      }

      env {
        name  = "APP_ENV"
        value = "production"
      }
    }
  }

  depends_on = [google_sql_database_instance.instance, google_secret_manager_secret_version.agent_key_version]
}

# Frontend Service
resource "google_cloud_run_v2_service" "frontend" {
  name     = "happyfde-dashboard"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/frontend:latest"
      
      ports {
        container_port = 3000
      }
      
      # Build-time arg NEXT_PUBLIC_API_URL should have been set during Docker build
      # But we can also set the env here in case the app supports it at runtime
      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
    }
  }
}

# Allow public access to both (Demo purpose)
resource "google_cloud_run_v2_service_iam_member" "noauth_api" {
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "noauth_front" {
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
