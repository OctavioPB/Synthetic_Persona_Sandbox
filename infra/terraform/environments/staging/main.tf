module "spb_staging" {
  source = "../../"

  environment           = "staging"
  aws_region            = "us-east-1"
  vpc_cidr              = "10.1.0.0/16"
  db_username           = var.db_username
  db_password           = var.db_password
  rds_instance_class    = "db.t3.small"
  rds_allocated_storage = 50
  redis_node_type       = "cache.t3.small"
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

terraform {
  backend "s3" {
    bucket = "spb-terraform-state-staging"
    key    = "staging/terraform.tfstate"
    region = "us-east-1"
  }
}
