module "spb_dev" {
  source = "../../"

  environment           = "dev"
  aws_region            = "us-east-1"
  vpc_cidr              = "10.0.0.0/16"
  db_username           = var.db_username
  db_password           = var.db_password
  rds_instance_class    = "db.t3.micro"
  rds_allocated_storage = 20
  redis_node_type       = "cache.t3.micro"
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
    bucket = "spb-terraform-state-dev"
    key    = "dev/terraform.tfstate"
    region = "us-east-1"
  }
}
