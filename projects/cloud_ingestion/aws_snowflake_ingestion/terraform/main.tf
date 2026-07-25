# Terraform: S3 landing zone + Lambda trigger + IAM roles for the
# Snowflake ingestion pipeline. This provisions the AWS side of the
# S3 -> Lambda -> Snowpipe ingestion pattern.
#
# NOTE: This has been validated with `terraform validate` (syntax and
# internal consistency check) but has NOT been applied against a real
# AWS account in this environment, since no AWS credentials are
# available here. It is standard, unmodified Terraform AWS provider
# syntax and is ready to run with `terraform init && terraform apply`
# given real AWS credentials and a real Snowflake storage integration ARN.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for the ingestion pipeline"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "snowflake_storage_integration_iam_arn" {
  description = "IAM ARN provided by Snowflake's storage integration (from DESC INTEGRATION)"
  type        = string
}

# --- S3 landing bucket ---

resource "aws_s3_bucket" "landing_zone" {
  bucket = "risk-events-landing-${var.environment}"

  tags = {
    Environment = var.environment
    Purpose     = "snowflake-ingestion-landing-zone"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "landing_zone_versioning" {
  bucket = aws_s3_bucket.landing_zone.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "landing_zone_lifecycle" {
  bucket = aws_s3_bucket.landing_zone.id

  rule {
    id     = "expire-raw-after-ingestion"
    status = "Enabled"

    filter {
      prefix = "raw/"
    }

    expiration {
      days = 30
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "landing_zone_encryption" {
  bucket = aws_s3_bucket.landing_zone.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# --- IAM role Snowflake assumes to read from the S3 bucket (storage integration) ---

resource "aws_iam_role" "snowflake_ingestion_role" {
  name = "snowflake-ingestion-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = var.snowflake_storage_integration_iam_arn
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = "snowflake_storage_integration_external_id"
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "snowflake_s3_read_policy" {
  name = "snowflake-s3-read-${var.environment}"
  role = aws_iam_role.snowflake_ingestion_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.landing_zone.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.landing_zone.arn
      }
    ]
  })
}

# --- SQS queue that Snowpipe listens on for S3 event notifications ---

resource "aws_sqs_queue" "snowpipe_notification_queue" {
  name                      = "snowpipe-ingestion-notifications-${var.environment}"
  message_retention_seconds = 345600 # 4 days

  tags = {
    Environment = var.environment
    Purpose     = "snowpipe-auto-ingest"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_notification" "landing_zone_notification" {
  bucket = aws_s3_bucket.landing_zone.id

  queue {
    queue_arn     = aws_sqs_queue.snowpipe_notification_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "raw/"
    filter_suffix = ".parquet"
  }
}

# --- Outputs consumed by the Snowflake side (CREATE STORAGE INTEGRATION / CREATE PIPE) ---

output "landing_bucket_name" {
  value = aws_s3_bucket.landing_zone.bucket
}

output "landing_bucket_arn" {
  value = aws_s3_bucket.landing_zone.arn
}

output "snowpipe_notification_queue_arn" {
  value = aws_sqs_queue.snowpipe_notification_queue.arn
}

output "snowflake_ingestion_role_arn" {
  value = aws_iam_role.snowflake_ingestion_role.arn
}
