# Cloud SQL Instance (PostgreSQL 16)
resource "google_sql_database_instance" "instance" {
  name             = "happyfde-db-instance"
  region           = var.region
  database_version = "POSTGRES_16"
  deletion_protection = false # Set to true for production!

  settings {
    tier = "db-f1-micro" # Smallest tier to keep costs low for the challenge

    ip_configuration {
      ipv4_enabled    = true # Allow public IP for initial setup if needed, but we use private connector
      private_network = google_compute_network.default.self_link
    }
  }

  depends_on = [
    google_project_service.sqladmin,
    google_service_networking_connection.private_vpc_connection
  ]
}

# The actual database
resource "google_sql_database" "database" {
  name     = "happyrobot"
  instance = google_sql_database_instance.instance.name
}

# The database user
resource "google_sql_user" "users" {
  name     = "postgres"
  instance = google_sql_database_instance.instance.name
  password = var.db_password
}
