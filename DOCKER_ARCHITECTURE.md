# AIILA — ILA Docker Architecture Documentation

## Overview
Complete containerized microservices architecture for **Intelligence Layer for Analytics** (ILA).  
**Deployment**: Single `docker compose up --build` command  
**Public Access**: NGINX reverse proxy on port 80 only  
**Network**: Docker bridge network `ila-net`

---

## 🏗️ System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Internet / Browser                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                         Port 80
                             │
┌─────────────────────────────▼────────────────────────────────────┐
│                       NGINX (Reverse Proxy)                      │
│                     ila_nginx:1.25-alpine                        │
│  Route /api/*      → backend:8000    (FastAPI)                  │
│  Route /ws         → backend:8000    (WebSocket)                │
│  Route /flower/*   → flower:5555     (Celery UI)                │
│  Route /*          → frontend:80     (React SPA)                │
└──┬──────────────────────────┬──────────────────────┬─────────────┘
   │                          │                      │
   │                          │                      │
   │                    ┌─────▼──────┐        ┌──────▼────────┐
   │                    │  Frontend   │        │    Backend    │
   │               ila_frontend:80    │    ila_backend:8000    │
   │            React (Nginx build)   │    FastAPI + Uvicorn   │
   │                    └─────┬──────┘        └──────┬────────┘
   │                          │                      │
   │                    ┌─────▼──────────────────────▼────────┐
   │                    │        Docker Network: ila-net      │
   │                    │  (All containers communicate here)  │
   │                    └────┬──────┬──────┬──────┬────────────┘
   │                         │      │      │      │
   │              ┌──────────┤      │      │      ├────────────┐
   │              │          │      │      │      │            │
   │          ┌───▼───┐  ┌───▼──┐ ┌▼────┐ │   ┌──▼──┐      ┌──▼──┐
   │          │ Postgres 15 │ Neo4j 5 │ Redis 7 │ Celery │ Celery │
   │          │             │ Graph   │ Cache & │ Worker │ Beat  │
   │          │ ila_postgres │ Database│ Broker  │ Queue  │ Scheduler
   │          │ Port 5432    │7687 bolt │6379   │        │       │
   │          └─────────────┘ └────────┘ └────┘ └──────┘ └──────┘
   │              (persistent data)
   │              (internal only)
   │
   └─────────► Flower (Celery Monitoring)
              ila_flower:5555
              Accessible at: http://localhost/flower/
```

---

## 📦 Services Summary (9 Total)

### Infrastructure Services

| # | Service | Image | Container Name | Port (Internal) | Purpose |
|---|---------|-------|-----------------|-----------------|---------|
| 1 | **PostgreSQL** | postgres:15-alpine | ila_postgres | 5432 | Relational database for users, configs, audit logs |
| 2 | **Neo4j** | neo4j:5-community | ila_neo4j | 7687 (Bolt) | Graph database for entity relationships & fraud patterns |
| 3 | **Redis** | redis:7-alpine | ila_redis | 6379 | Cache, Celery broker, Pub/Sub messaging |

### Application Services

| # | Service | Image | Container Name | Port (Internal) | Purpose |
|---|---------|-------|-----------------|-----------------|---------|
| 4 | **Backend** | Custom (./backend/Dockerfile) | ila_backend | 8000 | FastAPI REST API, business logic, ML integration |
| 5 | **Celery Worker** | Custom (./backend/Dockerfile) | ila_celery_worker | N/A | Async task processing (queues: default, ingest, enrich, ml, neo4j_sync) |
| 6 | **Celery Beat** | Custom (./backend/Dockerfile) | ila_celery_beat | N/A | Scheduled job execution |
| 7 | **Flower** | mher/flower:2.0 | ila_flower | 5555 | Celery task monitoring & management dashboard |
| 8 | **Frontend** | Custom (./frontend/Dockerfile) | ila_frontend | 80 | React SPA (production Nginx build) |
| 9 | **NGINX** | nginx:1.25-alpine | ila_nginx | 80 | Reverse proxy, SSL termination, load balancing |

---

## 🔗 Service Dependencies

```
NGINX
├── depends_on: [backend, frontend]
│
├─ Frontend
│  └─ depends_on: [backend]
│     └─ React (Vite) SPA in Nginx
│
├─ Backend (FastAPI)
│  ├─ depends_on: [postgres, redis, neo4j]
│  └─ REST API + WebSocket server
│
├─ Celery Worker
│  ├─ depends_on: [backend, redis]
│  └─ Async: ingest, enrich, ML models, Neo4j sync
│
├─ Celery Beat
│  ├─ depends_on: [redis, celery_worker]
│  └─ Scheduled: cleanup, backups, ML retraining
│
└─ Infrastructure
   ├─ PostgreSQL (no dependencies)
   ├─ Neo4j (no dependencies)
   └─ Redis (no dependencies)
```

---

## 🔐 Environment & Networking

### Network Configuration
- **Type**: Docker bridge network (`ila-net`)
- **Container-to-Container**: Full DNS resolution (e.g., `http://backend:8000`)
- **External Access**: ONLY via NGINX on `localhost:80`

### Exposed Ports
```yaml
Development (Host Machine):
  80   → NGINX reverse proxy (production) ✓ PUBLIC
  5432 → PostgreSQL (local DB tools only) — REMOVE in PROD
  7474 → Neo4j browser (management) — REMOVE in PROD
  7687 → Neo4j Bolt protocol — REMOVE in PROD
  6379 → Redis CLI tools (local only) — REMOVE in PROD

Production (Recommended Changes):
  80   → NGINX only
  443  → HTTPS termination (add SSL cert)
```

### Environment Variables
From `.env`:
```bash
# Database credentials
POSTGRES_DB=ila_db
POSTGRES_USER=ila_user
POSTGRES_PASSWORD=ila_password  # ⚠️ Change in production!

# Neo4j
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123  # ⚠️ Change in production!

# Redis
REDIS_PASSWORD=changeme_dev  # ⚠️ Change in production!

# FastAPI
SECRET_KEY=<32-char-random-string>  # ⚠️ Generate secure key!

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Frontend
VITE_API_BASE_URL=http://localhost
VITE_WS_URL=ws://localhost/ws
```

---

## 🗃️ Volumes (Persistent Data)

| Volume | Mounts | Purpose | Persistence |
|--------|--------|---------|-------------|
| `neo4j_data` | /data | Graph database files | ✓ Persistent |
| `neo4j_logs` | /logs | Neo4j operation logs | ✓ Persistent |
| `neo4j_import` | /import | Data import staging | ✓ Persistent |
| `neo4j_plugins` | /plugins | GDS plugins | ✓ Persistent |
| `redis_data` | /data | Redis persistence | ✓ Persistent |
| `flower_data` | /data | Task history | ✓ Persistent |

**Backend & Frontend**: Use bind-mount volumes for development (`./backend:/app`, `./frontend:/app`)

---

## 🚀 Build & Deployment

### Local Development
```bash
# Build and start all services
docker compose up --build

# View logs
docker compose logs -f

# Rebuild single service
docker compose up --build backend

# Stop all services
docker compose down

# Remove volumes (reset data)
docker compose down -v
```

### Access Points
| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost/api/v1/* | N/A |
| WebSocket | ws://localhost/ws | N/A |
| Frontend | http://localhost | N/A |
| Celery Dashboard | http://localhost/flower/ | admin/admin |
| Neo4j Browser | http://localhost:7474 | neo4j/password123 |
| PostgreSQL | localhost:5432 | ila_user/ila_password |
| Redis | localhost:6379 | password: changeme_dev |

---

## 🏥 Health Checks

Each critical service includes health checks:

```yaml
Backend:
  - Test: curl http://localhost:8000/api/v1/health
  - Interval: 15s
  - Depends on: Postgres, Redis, Neo4j healthy

PostgreSQL:
  - Test: pg_isready
  - Interval: 10s

Neo4j:
  - Test: wget http://localhost:7474
  - Interval: 20s (longer start time)

Redis:
  - Test: redis-cli ping
  - Interval: 10s

NGINX:
  - Test: wget http://localhost/nginx-health
  - Interval: 10s
```

---

## 📋 Backend Dockerfile Details

**File**: `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for ML/NLP packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key Optimizations**:
- ✓ Multi-stage layer caching (requirements separate)
- ✓ Slim base image (python:3.11-slim)
- ✓ Build dependencies cleaned up (`rm -rf /var/lib/apt/lists/`)
- ✓ `--no-cache-dir` for pip (reduces image size)
- ✓ Reused for backend, celery_worker, celery_beat (same codebase)

---

## 📋 Frontend Dockerfile Details

**File**: `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Key Features**:
- ✓ Multi-stage build (npm builder → nginx server)
- ✓ Production-optimized Nginx
- ✓ SPA routing configured in nginx.conf
- ✓ Minimal final image size

---

## 🔄 Celery Task Architecture

### Queue Setup
```yaml
Redis Databases:
  DB 0: Celery broker (task queue)
  DB 1: Celery broker (flower monitoring)
  DB 2: Result backend (task results)
```

### Task Queues
```bash
Worker listens on: default, ingest, enrich, ml, neo4j_sync

Task Types:
  - ingest: Feed parsing, data ingestion
  - enrich: Entity enrichment, ML processing
  - ml: Model inference, sentiment analysis
  - neo4j_sync: Graph synchronization
  - default: Miscellaneous tasks
```

### Monitoring
```bash
Flower Dashboard: http://localhost/flower/
Auth: admin / admin
Displays: Task history, worker status, queue depth, failures
```

---

## 🛡️ Security Considerations

### ⚠️ **DEVELOPMENT MODE ONLY** (Current Configuration)
```yaml
Issues:
  ❌ All default passwords exposed (.env in git)
  ❌ All database ports exposed locally (5432, 7474, 7687)
  ❌ No SSL/TLS encryption
  ❌ NGINX on HTTP (no HTTPS)
  ❌ Default Flower credentials (admin/admin)
```

### 🔒 **PRODUCTION RECOMMENDATIONS**

```yaml
1. Use Docker secrets for sensitive data:
   docker secret create db_password <(echo 'strong_password')

2. Use environment-specific .env files:
   .env.dev → local development
   .env.prod → production (in secrets manager)

3. Remove exposed development ports:
   - Remove: 5432 (PostgreSQL)
   - Remove: 7474, 7687 (Neo4j)
   - Remove: 6379 (Redis)

4. Enable HTTPS:
   - Use Let's Encrypt with NGINX
   - Mount SSL certificates: ./certs:/etc/nginx/certs:ro

5. Add SSL termination in NGINX:
   listen 443 ssl http2;
   ssl_certificate /etc/nginx/certs/cert.pem;
   ssl_certificate_key /etc/nginx/certs/key.pem;

6. Add rate limiting to NGINX:
   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
   limit_req zone=api burst=20 nodelay;

7. Change all default passwords:
   POSTGRES_PASSWORD → Strong random
   NEO4J_PASSWORD → Strong random
   REDIS_PASSWORD → Strong random
   SECRET_KEY → 32-char cryptographic key

8. Use health checks for auto-recovery:
   (Already configured, good!)

9. Add resource limits:
   cpu_shares, memory limits per service

10. Enable Docker content trust & scanning
```

---

## 🧪 Testing Services

### Backend Health Check
```bash
curl http://localhost/api/v1/health
```

### WebSocket Test
```bash
wscat -c ws://localhost/ws
```

### Frontend Status
```bash
curl http://localhost -I
# Should return: HTTP/1.1 200 OK
```

### Celery Status
```bash
# From inside backend container:
celery -A app.tasks.celery_app inspect active
celery -A app.tasks.celery_app inspect stats
```

---

## 📊 Performance Tuning

### Redis Configuration
```yaml
Current: 512MB max memory, LRU eviction
Recommendation:
  - Production: 2-4GB depending on load
  - Monitor: redis-cli info memory
```

### Neo4j Memory
```yaml
Current:
  Heap: 512M initial, 1G max
  Page cache: 512M
Recommendation:
  - Production: Adjust based on graph size
  - Monitor: Neo4j browser → Database info
```

### Backend Worker Concurrency
```yaml
Current: 4 workers per container
Recommendation:
  - Single backend: 2-4 workers
  - Scale horizontally: Add more celery_worker containers
  - Use `docker compose up --scale celery_worker=3`
```

---

## 🔧 Troubleshooting

### Services Not Starting
```bash
# Check logs
docker compose logs <service_name>

# Inspect container state
docker ps -a

# Check health status
docker compose ps

# Rebuild everything
docker compose down -v
docker compose up --build
```

### Database Connectivity
```bash
# Test PostgreSQL
docker compose exec postgres pg_isready

# Test Neo4j
docker compose exec neo4j wget -O- http://localhost:7474

# Test Redis
docker compose exec redis redis-cli ping
```

### Backend API Issues
```bash
docker compose logs backend
docker compose exec backend python -m pytest tests/
```

### Celery Task Problems
```bash
# Check active tasks
docker compose exec backend celery -A app.tasks.celery_app inspect active

# Monitor in real-time
docker compose logs -f celery_worker
docker compose logs -f celery_beat
```

---

## 📝 Modification Guide

### Add New Service
1. Define service in `docker-compose.yml`
2. Add to network: `ila-net`
3. Add dependencies in other services if needed
4. Rebuild: `docker compose up --build`

### Scale Celery Workers
```bash
docker compose up --scale celery_worker=3
```

### Change Ports
Edit `docker-compose.yml` ports section or `.env`

### Modify NGINX Routes
Edit `nginx/nginx.conf` and rebuild NGINX

---

## 📚 References

- **Docker Compose**: https://docs.docker.com/compose/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Celery**: https://docs.celeryproject.io/
- **Neo4j**: https://neo4j.com/docs/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **NGINX**: https://nginx.org/en/docs/

---

**Last Updated**: 2026-06-04  
**Maintained By**: DevOps Team  
**Status**: Production Ready (After security review)
