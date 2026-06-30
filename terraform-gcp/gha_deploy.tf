# gae_deployer account
resource "google_service_account" "gae_deployer" {
  project    = var.project_id
  account_id = var.gae_deployer_id
}

# gae_deployer roles
resource "google_project_iam_member" "gae_deployer_roles" {
  for_each = toset(local.gae_deployer_roles)

  project = var.project_id
  member  = "serviceAccount:${local.gae_deployer_sa_email}"
  role    = each.key
}

# Workload Identity Pool
resource "google_iam_workload_identity_pool" "github_pool" {
  project                   = var.project_id
  display_name              = "GitHub Actions Pool"
  workload_identity_pool_id = var.workload_pool_id
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
  project                            = var.project_id
  display_name                       = "GitHub Actions Provider"
  workload_identity_pool_id          = var.workload_pool_id
  workload_identity_pool_provider_id = var.workload_provider_id
  attribute_condition                = "assertion.repository == '${var.github_repo}'"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "gha_roles" {
  for_each = toset(local.gha_roles)

  service_account_id = "projects/${var.project_id}/serviceAccounts/${local.gae_deployer_sa_email}"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.github_repo}"
  role               = each.key
}
