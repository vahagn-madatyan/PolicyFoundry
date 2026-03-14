---
estimated_steps: 4
estimated_files: 4
---

# T03: Terraform HCL for test VPC with Security Groups and Flow Logs

**Slice:** S10 — Infrastructure And Packaging
**Milestone:** M001

## Description

Write Terraform HCL in `infra/terraform/` that provisions an AWS test environment: VPC with public/private subnets, Security Group with sample ingress/egress rules, S3 bucket for Flow Log delivery, IAM role for the Flow Log service, and a VPC Flow Log resource writing Parquet to S3. Delivers INFRA-01.

## Steps

1. Create `infra/terraform/versions.tf` — require Terraform >= 1.9, AWS provider >= 5.0. Include a `random` provider for S3 bucket suffix.
2. Create `infra/terraform/variables.tf` — variables for `aws_region` (default `us-east-1`), `vpc_cidr` (default `10.0.0.0/16`), `name_prefix` (default `policyfoundry-test`).
3. Create `infra/terraform/main.tf` — all resources: VPC, 2 subnets (public `10.0.1.0/24`, private `10.0.2.0/24`), Security Group with separate `aws_vpc_security_group_ingress_rule` (SSH from VPC CIDR, HTTPS from anywhere) and `aws_vpc_security_group_egress_rule` (all outbound) resources, `random_id` for bucket suffix, S3 bucket with bucket policy for `delivery.logs.amazonaws.com`, IAM role + policy for Flow Log delivery, VPC Flow Log targeting the VPC with S3 destination in Parquet format and per-hour partitioning.
4. Create `infra/terraform/outputs.tf` — outputs for `vpc_id`, `security_group_id`, `flow_log_bucket_name`, `flow_log_id`.

## Must-Haves

- [ ] VPC with 2 subnets (public/private)
- [ ] Security Group with sample rules using separate ingress/egress rule resources
- [ ] S3 bucket with random suffix and bucket policy for Flow Log delivery
- [ ] IAM role with permissions for VPC Flow Log delivery to S3
- [ ] VPC Flow Log resource writing Parquet to S3
- [ ] `terraform validate` passes

## Verification

- `cd infra/terraform && terraform init -backend=false && terraform validate` passes (or HCL review if terraform unavailable)
- Resources cover: VPC, 2 subnets, SG, 2+ SG rules, S3 bucket, bucket policy, IAM role, IAM policy, Flow Log

## Inputs

- S10 Research — Terraform >= 1.9, separate ingress/egress rule resources, Parquet format, IAM requirements
- M001 Research — plain HCL (NOT CDKTF)

## Expected Output

- `infra/terraform/versions.tf` — provider version constraints
- `infra/terraform/variables.tf` — configurable inputs
- `infra/terraform/main.tf` — all AWS resources
- `infra/terraform/outputs.tf` — key resource IDs and names
