output "backend_url" {
  description = "The URL of the backend API"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "The URL of the executive dashboard"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "db_instance_ip" {
  description = "The private IP of the Cloud SQL instance"
  value       = google_sql_database_instance.instance.private_ip_address
}
