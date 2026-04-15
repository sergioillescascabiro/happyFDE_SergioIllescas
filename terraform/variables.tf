variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "db_password" {
  description = "The password for the PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "agent_api_key" {
  description = "The API key for the HappyRobot agent"
  type        = string
  sensitive   = true
}

variable "dashboard_token" {
  description = "The token for the Executive Dashboard"
  type        = string
  sensitive   = true
}

