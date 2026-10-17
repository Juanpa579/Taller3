terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"
  # ~/.aws/credentials (the same ones created by `aws configure`).
}


data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}

resource "aws_security_group" "ec2" {
  name        = "lab-ec2-sg"
  description = "Grupo de seguridad para la instancia de EC2 de la actividad"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "lab-ec2-sg" }
}

resource "aws_security_group" "rds" {
  name        = "lab-rds-sg"
  description = "Solo permite PostgreSQL desde la instancia de EC2 de la actividad"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = { Name = "lab-rds-sg" }
}

resource "aws_s3_bucket" "lab" {
  bucket        = "lab-bucket-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_instance" "lab" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.micro"
  vpc_security_group_ids = [aws_security_group.ec2.id]

  tags = { Name = "lab-ec2" }
}

resource "aws_db_instance" "lab" {
  identifier        = "lab-db"
  engine            = "postgres"
  instance_class    = "db.t3.micro"
  allocated_storage = 20

  username = "dbadmin"
  manage_master_user_password = true

  vpc_security_group_ids  = [aws_security_group.rds.id]
  publicly_accessible     = false
  backup_retention_period = 0 
  skip_final_snapshot     = true
}

output "bucket_name" {
  value = aws_s3_bucket.lab.bucket
}

output "ec2_instance_id" {
  value = aws_instance.lab.id
}

output "rds_endpoint" {
  value = aws_db_instance.lab.endpoint
}

output "rds_secret_arn" {
  value = aws_db_instance.lab.master_user_secret[0].secret_arn
}
