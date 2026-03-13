output "vpc_id" {
  description = "ID of the test VPC"
  value       = aws_vpc.main.id
}

output "security_group_id" {
  description = "ID of the sample security group"
  value       = aws_security_group.main.id
}

output "flow_log_bucket_name" {
  description = "Name of the S3 bucket receiving VPC Flow Logs"
  value       = aws_s3_bucket.flow_logs.id
}

output "flow_log_id" {
  description = "ID of the VPC Flow Log"
  value       = aws_flow_log.main.id
}
