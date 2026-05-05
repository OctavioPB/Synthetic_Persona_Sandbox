terraform {
  required_version = ">= 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# ── Shared locals ──────────────────────────────────────────────────────────────
locals {
  project = "synthetic-persona-sandbox"
  common_tags = {
    Project     = local.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── Networking ─────────────────────────────────────────────────────────────────
module "vpc" {
  source = "./modules/vpc"

  project     = local.project
  environment = var.environment
  cidr_block  = var.vpc_cidr
  tags        = local.common_tags
}

# ── PostgreSQL (RDS) ───────────────────────────────────────────────────────────
module "postgres" {
  source = "./modules/rds"

  project            = local.project
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  db_name            = "synthetic_persona"
  db_username        = var.db_username
  db_password        = var.db_password
  instance_class     = var.rds_instance_class
  allocated_storage  = var.rds_allocated_storage
  tags               = local.common_tags
}

# ── ElastiCache (Redis) ────────────────────────────────────────────────────────
module "redis" {
  source = "./modules/elasticache"

  project      = local.project
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnet_ids
  node_type    = var.redis_node_type
  tags         = local.common_tags
}
