# Tests — Cross-Service Integration Tests

> **Status: Not yet implemented** (planned for a future chunk)

This directory will contain integration and end-to-end tests that span multiple services:

- **API integration tests** — backend endpoints with real MongoDB and Redis
- **Agent workflow tests** — multi-agent orchestration scenarios
- **Data pipeline tests** — ML ingestion and inference pipelines
- **End-to-end tests** — full user flows via Playwright or Cypress

## Current Testing

Backend unit and API tests live in `backend/tests/` and are run with:

```bash
cd backend && pytest tests/ -v
```

Cross-service tests will be added to this directory once the services they test are implemented.
