# STAR
# Situation: Reviewers need to see how the AWS examples would be deployed.
# Task: Sketch the core infrastructure without locking into a specific account.
# Action: Declare S3 buckets, Glue job placeholder, Kinesis stream, and MSK comments.
# Result: Provides an infrastructure conversation starter for interviews.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

resource "aws_s3_bucket" "landing" {
  bucket_prefix = "portfolio-landing-"
}

resource "aws_s3_bucket" "curated" {
  bucket_prefix = "portfolio-curated-"
}

resource "aws_kinesis_stream" "events" {
  name        = "portfolio-events"
  shard_count = 1
}

# Add Glue job, Lambda permissions, MSK cluster, and CloudWatch alarms in real deployment.
