# STAR
# Situation: Azure examples need a deployable infrastructure outline.
# Task: Capture core resources without binding to one subscription.
# Action: Sketch resource group, storage account, Event Hubs namespace, and Function App placeholders.
# Result: Shows infrastructure awareness for Azure big data projects.

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "portfolio" {
  name     = "rg-big-data-portfolio"
  location = "eastus"
}

resource "azurerm_storage_account" "lake" {
  name                     = "portfoliolakeexample"
  resource_group_name      = azurerm_resource_group.portfolio.name
  location                 = azurerm_resource_group.portfolio.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true
}

# Add Event Hubs, Databricks workspace, Function App, and Azure Monitor alerts in real deployment.
