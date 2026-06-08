# STAR
# Situation: GCP examples need infrastructure context for review.
# Task: Sketch storage, Pub/Sub, and BigQuery resources.
# Action: Declare minimal Terraform resources that can be extended for Dataproc and Dataflow.
# Result: Demonstrates cloud infrastructure awareness without forcing one deployment.

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

variable "project_id" {
  type = string
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
}

resource "google_storage_bucket" "landing" {
  name                        = "portfolio-landing-${var.project_id}"
  location                    = "US"
  uniform_bucket_level_access = true
}

resource "google_pubsub_topic" "events" {
  name = "portfolio-events"
}

resource "google_bigquery_dataset" "curated" {
  dataset_id = "portfolio_curated"
  location   = "US"
}
