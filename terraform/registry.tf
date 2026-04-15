# Repository to store our backend and frontend images
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "happyfde-repo"
  description   = "Docker repository for HappyFDE components"
  format        = "DOCKER"

  depends_on = [google_project_service.compute] # Compute API is often a pre-req for AR
}
