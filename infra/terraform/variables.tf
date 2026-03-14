variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "name_prefix" {
  description = "Prefix for resource names and tags"
  type        = string
  default     = "policyfoundry-test"
}
