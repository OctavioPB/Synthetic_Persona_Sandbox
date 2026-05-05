module "spb_prod" {
  source = "../../"

  environment           = "prod"
  aws_region            = "us-east-1"
  vpc_cidr              = "10.2.0.0/16"
  db_username           = var.db_username
  db_password           = var.db_password
  rds_instance_class    = "db.t3.medium"
  rds_allocated_storage = 100
  redis_node_type       = "cache.t3.medium"
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
    bucket = "spb-terraform-state-prod"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}
