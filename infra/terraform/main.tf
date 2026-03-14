################################################################################
# Data sources
################################################################################

data "aws_caller_identity" "current" {}

################################################################################
# VPC and Subnets
################################################################################

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.name_prefix}-vpc"
  }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "${var.name_prefix}-public"
  }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "${var.name_prefix}-private"
  }
}

################################################################################
# Security Group with separate ingress/egress rule resources
################################################################################

resource "aws_security_group" "main" {
  name        = "${var.name_prefix}-sg"
  description = "Sample security group for PolicyFoundry test environment"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${var.name_prefix}-sg"
  }
}

# Ingress: SSH from within VPC CIDR
resource "aws_vpc_security_group_ingress_rule" "ssh_from_vpc" {
  security_group_id = aws_security_group.main.id
  description       = "SSH from VPC CIDR"
  cidr_ipv4         = var.vpc_cidr
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"

  tags = {
    Name = "${var.name_prefix}-ssh-ingress"
  }
}

# Ingress: HTTPS from anywhere
resource "aws_vpc_security_group_ingress_rule" "https_from_anywhere" {
  security_group_id = aws_security_group.main.id
  description       = "HTTPS from anywhere"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"

  tags = {
    Name = "${var.name_prefix}-https-ingress"
  }
}

# Egress: all outbound traffic
resource "aws_vpc_security_group_egress_rule" "all_outbound" {
  security_group_id = aws_security_group.main.id
  description       = "Allow all outbound traffic"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"

  tags = {
    Name = "${var.name_prefix}-all-egress"
  }
}

################################################################################
# S3 Bucket for Flow Log delivery
################################################################################

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "flow_logs" {
  bucket = "${var.name_prefix}-flow-logs-${random_id.bucket_suffix.hex}"

  tags = {
    Name = "${var.name_prefix}-flow-logs"
  }
}

resource "aws_s3_bucket_policy" "flow_logs" {
  bucket = aws_s3_bucket.flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSLogDeliveryWrite"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.flow_logs.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl"      = "bucket-owner-full-control"
            "aws:SourceAccount"  = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "AWSLogDeliveryAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.flow_logs.arn
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
    ]
  })
}

################################################################################
# IAM Role for VPC Flow Log delivery
################################################################################

resource "aws_iam_role" "flow_log" {
  name = "${var.name_prefix}-flow-log-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:vpc-flow-log/*"
          }
        }
      },
    ]
  })

  tags = {
    Name = "${var.name_prefix}-flow-log-role"
  }
}

resource "aws_iam_role_policy" "flow_log" {
  name = "${var.name_prefix}-flow-log-policy"
  role = aws_iam_role.flow_log.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetBucketAcl",
        ]
        Resource = [
          aws_s3_bucket.flow_logs.arn,
          "${aws_s3_bucket.flow_logs.arn}/*",
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
        ]
        Resource = "*"
      },
    ]
  })
}

################################################################################
# VPC Flow Log — Parquet to S3 with hourly partitioning
################################################################################

resource "aws_flow_log" "main" {
  vpc_id               = aws_vpc.main.id
  traffic_type         = "ALL"
  log_destination      = aws_s3_bucket.flow_logs.arn
  log_destination_type = "s3"
  iam_role_arn         = aws_iam_role.flow_log.arn

  destination_options {
    file_format                = "parquet"
    hive_compatible_partitions = true
    per_hour_partition         = true
  }

  tags = {
    Name = "${var.name_prefix}-flow-log"
  }
}
