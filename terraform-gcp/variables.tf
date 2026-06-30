variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "project_number" {
  description = "Google Cloud Project Number"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "asia-northeast1"
}

variable "github_repo" {
  description = "GitHub repository (user/repo)"
  type        = string
}

variable "gae_deployer_id" {
  description = "GAE Deployer Service Account ID"
  type        = string
}

variable "workload_pool_id" {
  description = "Workload Identity Pool ID"
  type        = string
}

variable "workload_provider_id" {
  description = "OIDC provider ID"
  type        = string
}

locals {
  gae_sys_sa_email      = "${var.project_id}@appspot.gserviceaccount.com"
  gae_deployer_sa_email = "${var.gae_deployer_id}@${var.project_id}.iam.gserviceaccount.com"

  gae_sys_sa_roles = [
    "roles/artifactregistry.reader",
    "roles/artifactregistry.writer",
    "roles/logging.logWriter",
    "roles/storage.admin",
  ]

  gae_deployer_roles = [
    "roles/appengine.appAdmin",
    "roles/artifactregistry.reader",
    "roles/cloudbuild.builds.editor",
    "roles/iam.serviceAccountUser",
    "roles/storage.admin",
  ]

  gha_roles = [
    "roles/iam.workloadIdentityUser",
    "roles/iam.serviceAccountTokenCreator"
  ]
}
