output "app_url" {
  value = "https://${google_app_engine_application.app.default_hostname}"
}

output "service_account_email" {
  value = local.gae_deployer_sa_email
}

output "workload_identity_provider_path" {
  value = google_iam_workload_identity_pool_provider.github_provider.name
}
