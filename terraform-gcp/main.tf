resource "google_app_engine_application" "app" {
  project     = var.project_id
  location_id = var.region
}

# gae_sys_sa roles
resource "google_project_iam_member" "gae_sys_sa_roles" {
  for_each = toset(local.gae_sys_sa_roles)

  project = var.project_id
  member  = "serviceAccount:${local.gae_sys_sa_email}"
  role    = each.key
}
