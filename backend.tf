terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "satfstatekongs001"
    container_name       = "tfstate"
    key                  = "poc/aks.tfstate"
  }
}

provider "azurerm" {
  features {}
  subscription_id = "7908ea24-a708-4291-be15-98426e3e9ca5"
}
