# Developer Setup Guide

> HospitalOps AI — Chunk 0.3 — Docker Runtime Validation & Dev Environment Hardening

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker Desktop | 24+ | Container runtime (includes Compose V2) |
| Docker Compose | V2 | Multi-service orchestration |
| Python | 3.11+ | Backend development (local, without Docker) |
| Node.js | 20+ | Frontend development (local, without Docker) |
| npm | 10+ | Frontend package management |
| Git | any | Version control |

> **Windows users**: Use Docker Desktop with WSL2 backend enabled.
> All `docker compose` commands run identically in PowerShell and Windows Terminal.

---

## Initial Setup

```bash
# Clone the repository
git clone <repo-url>
cd hospitalops-ai

# Copy environment file
cp .env.example .env      # macOS/Linux
# OR
copy .env.example .env    # Windows Command Prompt
# OR
Copy-Item .env.example .env  # Windows PowerShell
```

The default `.env` values work for local Docker development without modification.

---

## Option 1: Docker (Recommended)

### Start all services

```bash
docker compose up --build -d
```

This builds all images and starts all four services in the background.

### Verify all services are healthy

```bash
docker compose ps
```

Wait until all services show `(healthy)`:

```
NAME                      STATUS
hospitalops-backend       Up (healthy)
hospitalops-frontend      Up (healthy)
hospitalops-mongodb       Up (healthy)
hospitalops-redis         Up (healthy)
```

> Health checks have `start_period` delays. MongoDB takes up to 20s, backend 15s, frontend 30s.

### Verify backend health endpoint

```bash
curl http://localhost:8000/api/v1/health
```

Expected:
```json
{
  "status": "ok",
  "app_name": "HospitalOps AI",
  "version": "0.1.0",
  "timestamp": "...",
  "chunk": "0.1 \u2014 Foundation"
}
```

### Verify frontend is running

Open in browser: **http://localhost:5173**

The HospitalOps AI foundation screen should render.

---

## Docker Command Reference

### Start / Stop

```bash
docker compose up -d                   # Start all services (detached)
docker compose up --build -d           # Rebuild images, then start
docker compose down                    # Stop containers, keep volumes (data preserved)
docker compose down -v                 # Stop AND delete volumes (resets database)
docker compose restart backend         # Restart one service without rebuild
```

### Build

```bash
docker compose build                   # Build all images (use cached layers)
docker compose build --no-cache        # Full clean rebuild (no cached layers)
docker compose build backend           # Build only the backend image
docker compose build frontend          # Build only the frontend image
```

### Logs

```bash
docker compose logs                    # All services, current output
docker compose logs -f                 # All services, live tail
docker compose logs backend            # Backend only
docker compose logs -f backend         # Backend, live tail
docker compose logs -f frontend        # Frontend, live tail
docker compose logs --tail=50 backend  # Last 50 lines of backend
```

### Status and inspection

```bash
docker compose ps                       # Container status + health state
docker compose ps --format json         # Machine-readable output
docker stats                            # Live CPU/memory per container
```

### Service-specific commands

```bash
# MongoDB shell
docker compose exec mongodb mongosh hospitalops

# MongoDB admin ping
docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Redis CLI
docker compose exec redis redis-cli

# Redis ping
docker compose exec redis redis-cli ping

# Backend shell (Python REPL in container)
docker compose exec backend python

# Backend shell (bash)
docker compose exec backend bash
```

---

## Frontend ↔ Backend Connectivity (Docker)

```
Browser → http://localhost:5173
              ↓
    Vite dev server (frontend container)
    /api/* requests proxied to http://backend:8000
              ↓
    FastAPI uvicorn (backend container)
              ↓
    MongoDB (mongodb container)  /  Redis (redis container)
```

**Why `backend:8000` and not `localhost:8000`?**

Inside the Docker network, each container's `localhost` refers to itself.
The Vite proxy must use the Docker service name `backend` to reach the backend container
over the `hospitalops-network` bridge network.

This is handled automatically by the `VITE_API_TARGET=http://backend:8000` environment
variable in `docker-compose.yml`. No manual configuration is needed.

For local development (outside Docker), `VITE_API_TARGET` defaults to `http://localhost:8000`.

---

## Persistence Validation

MongoDB and Redis use named Docker volumes for persistence.

To verify persistence:

```bash
# 1. Start services
docker compose up -d

# 2. Confirm volumes exist
docker volume ls | grep hospitalops

# Expected:
# local   hospitalops-ai_mongodb-data
# local   hospitalops-ai_mongodb-config
# local   hospitalops-ai_redis-data

# 3. Stop containers (volumes preserved)
docker compose down

# 4. Start again — services restore from volumes
docker compose up -d

# 5. Confirm healthy state
docker compose ps
```

> Volumes are deleted only with `docker compose down -v`. Do not use `-v` during normal development.

---

## Option 2: Local Development (Without Docker)

You must have MongoDB and Redis running separately (Docker or installed locally).

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
# Activate (Windows CMD)
.venv\Scripts\activate.bat
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env — update MONGODB_URI and REDIS_URL to point to your local instances
# e.g. MONGODB_URI=mongodb://localhost:27017
#      REDIS_URL=redis://localhost:6379

# Run the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Available at:
- API: http://localhost:8000/api/v1/
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Available at: http://localhost:5173

The Vite proxy defaults to `http://localhost:8000` for the backend when running locally.

---

## Running Tests & Checks

All commands assume the virtual environment is activated (backend) or you are in the correct directory.

### Backend tests

```bash
cd backend
.venv\Scripts\pytest tests/ -v        # Windows
.venv/bin/pytest tests/ -v            # macOS/Linux
```

### Backend lint

```bash
cd backend
.venv\Scripts\ruff check .            # Windows
.venv/bin/ruff check .                # macOS/Linux
```

### Frontend build verification

```bash
cd frontend
npm run build
```

### Frontend lint

```bash
cd frontend
npm run lint
```

---

## Troubleshooting

### Backend unhealthy / not starting

```bash
docker compose logs backend
```

Common causes:
- MongoDB not yet healthy (backend waits for `service_healthy`)
- Python dependency installation failed during build
- Port 8000 already in use on host

### Frontend not loading

```bash
docker compose logs frontend
```

Common causes:
- `npm ci` failed during build (check network connectivity)
- Port 5173 already in use on host
- Vite slow to start (health check `start_period` is 30s — wait)

### MongoDB connection refused

```bash
docker compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

If this fails, MongoDB is not yet ready. Wait for `(healthy)` status.

### Port conflicts

If ports 8000, 5173, 27017, or 6379 are already in use on your host,
override them in `.env`:

```env
BACKEND_PORT=8001
FRONTEND_PORT=5174
```

Then restart: `docker compose down && docker compose up -d`

### Windows: bind mount permissions

If the backend container cannot read/write files due to bind mount permission errors,
ensure WSL2 integration is enabled in Docker Desktop settings for your distro.

### Full reset

```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

---

## Environment Variables Reference

See `.env.example` at the repository root for all variables.

| Variable | Docker Default | Local Default | Description |
|---|---|---|---|
| `MONGODB_URI` | `mongodb://mongodb:27017` | `mongodb://localhost:27017` | MongoDB URI |
| `MONGODB_DATABASE` | `hospitalops` | `hospitalops` | Database name |
| `REDIS_URL` | `redis://redis:6379` | `redis://localhost:6379` | Redis URL |
| `CORS_ORIGINS` | `http://localhost:5173,...` | same | Allowed origins |
| `LOG_LEVEL` | `INFO` | `INFO` | Log verbosity |
| `VITE_API_TARGET` | `http://backend:8000` | not set (defaults to localhost) | Vite proxy target |

---

## Project Structure Reference

```
hospitalops-ai/
├── frontend/
│   ├── src/
│   │   ├── api/client.ts    Typed API client
│   │   ├── App.tsx          Application shell
│   │   └── vite-env.d.ts    Vite type declarations
│   ├── vite.config.ts       Vite + proxy config
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── api/v1/          Route handlers
│   │   ├── core/            Config, logging, exceptions
│   │   ├── models/          Base domain models
│   │   └── schemas/         Pydantic schemas
│   ├── tests/               pytest test suite
│   └── Dockerfile
├── docs/
│   ├── architecture/        System architecture (6 documents)
│   ├── decisions/           ADRs 001–005
│   └── development/         This file
├── docker-compose.yml       Local dev environment
├── .env.example             All env variables documented
└── AGENTS.md                Engineering constitution
```
