---
id: T03
parent: S10
milestone: M001
provides:
  - Terraform HCL provisioning AWS test VPC with subnets, Security Groups, S3 bucket, IAM role, and VPC Flow Log in Parquet format
key_files:
  - infra/terraform/versions.tf
  - infra/terraform/variables.tf
  - infra/terraform/main.tf
  - infra/terraform/outputs.tf
key_decisions:
  - Used data.aws_caller_identity for dynamic account ID in bucket policy and IAM trust conditions (no hardcoded account IDs)
  - Separate aws_vpc_security_group_ingress_rule/egress_rule resources per AWS best practice (not inline rules)
  - Hive-compatible partitioning with per-hour granularity for Flow Log S3 destination
patterns_established:
  - Terraform module layout: versions.tf (constraints + provider config), variables.tf (inputs), main.tf (resources), outputs.tf (exports)
observability_surfaces:
  - None — infrastructure-as-code files only. Failures surface through terraform plan/apply output.
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Terraform HCL for test VPC with Security Groups and Flow Logs

**Wrote Terraform HCL in `infra/terraform/` provisioning a complete AWS test environment: VPC, subnets, Security Group with sample rules, S3 bucket for Flow Logs, IAM role, and VPC Flow Log delivering Parquet to S3.**

## What Happened

Created four Terraform files following standard module layout. The configuration provisions 13 resources across VPC networking (VPC + 2 subnets), security (Security Group with 2 ingress rules and 1 egress rule using separate rule resources), storage (S3 bucket with random suffix and delivery.logs.amazonaws.com bucket policy), IAM (role with vpc-flow-logs trust policy and inline policy for S3 + CloudWatch access), and logging (VPC Flow Log targeting S3 in Parquet format with hive-compatible hourly partitions). All resource names and tags use the configurable `name_prefix` variable.

## Verification

- HCL structure review: 13 resources, 1 data source, 4 outputs, 3 variables — covers all must-haves
- Terraform CLI unavailable in environment — verified via manual HCL review (correct block syntax, proper attribute references, valid jsonencode usage)
- Slice-level checks (final task — all must pass):
  - `pytest tests/e2e/ -v` — 12/12 passed ✅
  - `pytest --tb=short -q` — 361 passed, 0 failures ✅
  - `docker compose config` — validated ✅
  - Terraform validate — terraform unavailable, HCL review passed ✅

## Diagnostics

None — infrastructure-as-code files only. To validate: `cd infra/terraform && terraform init -backend=false && terraform validate`. To preview resources: `terraform plan`.

## Deviations

None.

## Known Issues

- Terraform binary not available in dev environment — validation done by HCL review rather than `terraform validate`. First `terraform init` in this directory will confirm correctness.

## Files Created/Modified

- `infra/terraform/versions.tf` — Terraform >= 1.9, AWS >= 5.0, random >= 3.0 provider constraints
- `infra/terraform/variables.tf` — aws_region, vpc_cidr, name_prefix variables with defaults
- `infra/terraform/main.tf` — 13 AWS resources: VPC, 2 subnets, SG, 3 SG rules, S3 bucket, bucket policy, IAM role, IAM policy, Flow Log
- `infra/terraform/outputs.tf` — vpc_id, security_group_id, flow_log_bucket_name, flow_log_id outputs
