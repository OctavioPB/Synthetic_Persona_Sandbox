output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "postgres_endpoint" {
  description = "PostgreSQL RDS endpoint"
  value       = module.postgres.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}
