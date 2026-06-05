variable "location" {
  type    = string
  default = "eastus"
}
variable "cluster_name" {
  type    = string
  default = "aks-kongs-poc"
}
variable "resource_group_name" {
  type    = string
  default = "rg-kongs-poc"
}
variable "kubernetes_version" {
  type    = string
  default = "1.34"
}
variable "node_vm_size" {
  type    = string
  default = "Standard_D2s_v7"
}
