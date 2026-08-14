# Infrastructure

> **Status: Not yet implemented** (planned for a future chunk)

This directory will contain infrastructure-as-code and deployment configuration:

- **Kubernetes manifests** — production container orchestration
- **Helm charts** — parameterized Kubernetes deployments
- **CI/CD pipelines** — GitHub Actions or equivalent
- **Terraform / cloud IaC** — cloud resource provisioning
- **Monitoring** — Prometheus, Grafana, alerting
- **Secrets management** — Vault or cloud-native secrets

## Current State

For local development, use `docker-compose.yml` at the repository root.

Production deployment infrastructure will be introduced in a later chunk when
the application has meaningful functionality to deploy.
