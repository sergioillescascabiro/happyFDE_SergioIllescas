# Default VPC for the project
resource "google_compute_network" "default" {
  name                    = "happyfde-network"
  auto_create_subnetworks = true
}

# Connector for Cloud Run to access the private SQL IP
resource "google_vpc_access_connector" "connector" {
  name          = "happyfde-vpc-connector"
  region        = var.region
  network       = google_compute_network.default.name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 3

  depends_on = [google_project_service.vpcaccess]
}

# 1. Reservar rango de IPs internas para servicios de Google
resource "google_compute_global_address" "private_ip_address" {
  name          = "happyfde-private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.default.id
}

# 2. Crear el túnel (Peering) entre nuestra red y la red de servicios de Google
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.default.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]

  depends_on = [google_project_service.servicenetworking]
}
