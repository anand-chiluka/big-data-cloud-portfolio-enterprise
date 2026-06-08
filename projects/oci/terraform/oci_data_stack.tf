# STAR
# Situation: OCI examples need infrastructure context for Object Storage, Streaming, and Data Flow.
# Task: Provide a Terraform outline that can be adapted to a tenancy.
# Action: Declare variables and placeholders for core OCI resources.
# Result: Demonstrates OCI infrastructure thinking without exposing tenancy specific values.

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0"
    }
  }
}

variable "compartment_ocid" {
  type = string
}

resource "oci_objectstorage_bucket" "landing" {
  compartment_id = var.compartment_ocid
  name           = "portfolio_landing"
  namespace      = var.namespace
}

variable "namespace" {
  type = string
}

# Add oci_streaming_stream, oci_dataflow_application, function app, dynamic groups, and policies in real deployment.
