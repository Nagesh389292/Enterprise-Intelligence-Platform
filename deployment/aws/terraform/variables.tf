variable "aws_region" {
  description = "AWS deployment target region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment stage"
  type        = string
  default     = "production"
}

variable "app_name" {
  description = "Application infrastructure stack name"
  type        = string
  default     = "nexacore-enterprise-platform"
}

variable "db_password" {
  description = "Database master administrator password"
  type        = string
  sensitive   = true
  default     = "nexacore_secure_cloud_pass_2026"
}
