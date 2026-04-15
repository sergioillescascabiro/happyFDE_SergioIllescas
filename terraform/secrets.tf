# Secret for Agent API Key
resource "google_secret_manager_secret" "agent_key" {
  secret_id = "agent-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "agent_key_version" {
  secret = google_secret_manager_secret.agent_key.id
  secret_data = var.agent_api_key
}

# Secret for Dashboard Token
resource "google_secret_manager_secret" "dashboard_token" {
  secret_id = "dashboard-token"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "dashboard_token_version" {
  secret = google_secret_manager_secret.dashboard_token.id
  secret_data = var.dashboard_token
}
