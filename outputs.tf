output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.aks.name
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.rg.name
}

output "law_workspace_id" {
  description = "Log Analytics Workspace ID for Container Insights"
  value       = azurerm_log_analytics_workspace.law.id
}

output "aks_oidc_issuer" {
  description = "OIDC Issuer URL (for workload identity)"
  value       = azurerm_kubernetes_cluster.aks.oidc_issuer_url
}

output "kube_config" {
  description = "Kubernetes config file content (sensitive)"
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
}

output "aks_fqdn" {
  description = "FQDN of the AKS cluster"
  value       = azurerm_kubernetes_cluster.aks.fqdn
}

output "node_resource_group" {
  description = "Auto-created resource group for AKS nodes"
  value       = azurerm_kubernetes_cluster.aks.node_resource_group
}

output "kubelet_identity" {
  description = "Kubelet identity for workload identity"
  value       = azurerm_kubernetes_cluster.aks.kubelet_identity[0].client_id
}
