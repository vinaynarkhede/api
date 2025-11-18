# API Gateway - Production-Ready Python Implementation

A modern, enterprise-grade API Gateway built with Python and FastAPI. This gateway provides comprehensive routing, authentication, rate limiting, caching, circuit breaking, service discovery, load balancing, multi-tenancy, audit logging, and complete monitoring for microservices architectures.

## 🚀 Features

### Core Features
- **Dynamic Request Routing** - Route requests to upstream services based on URL patterns with path parameter extraction
- **Multiple Load Balancing Strategies** - Round-robin, least-connections, weighted, consistent hashing, and random distribution
- **Service Discovery** - HashiCorp Consul integration for dynamic service registration and health monitoring
- **Request ID Propagation** - Distributed tracing with automatic request ID generation and propagation

### Security & Authentication
- **JWT Authentication** - Secure token-based authentication with configurable expiration
- **API Key Management** - Database-backed API key generation, validation, and revocation
- **OAuth 2.0 Support** - Password grant and client credentials flows
- **SSO Integration** - Support for Google, GitHub, and Azure AD authentication
- **Session Management** - Database-backed sessions with device tracking and revocation
- **Secrets Management** - HashiCorp Vault integration for secure secret storage
- **CORS Handling** - Configurable Cross-Origin Resource Sharing
- **Request Validation** - SQL injection, XSS, and path traversal protection
- **Security Headers** - Automatic security header injection (HSTS, CSP, X-Frame-Options)
- **Audit Logging** - Comprehensive audit trail for compliance (SOC 2, GDPR, HIPAA)

### Performance & Reliability
- **Rate Limiting** - Token bucket and sliding window algorithms with Redis backend
- **Response Caching** - Distributed caching with configurable TTL
- **Circuit Breaker** - Prevent cascading failures with automatic recovery
- **Retry Logic** - Exponential backoff for transient failures
- **Timeout Management** - Configurable timeouts for upstream requests
- **Connection Pooling** - Efficient HTTP connection management

### Monitoring & Observability
- **Structured Logging** - JSON logging with structlog and automatic context binding
- **Prometheus Metrics** - 25+ metrics covering requests, errors, latency, cache, circuit breakers
- **Distributed Tracing** - OpenTelemetry integration for request tracing
- **Health Checks** - Kubernetes-ready liveness, readiness, and dependency checks
- **Alerting Rules** - 20+ pre-configured Prometheus alerts for operational issues

### Enterprise Features
- **Multi-Tenancy** - Tenant isolation with quota management
- **Admin API** - Runtime configuration, route management, circuit breaker control
- **PostgreSQL Persistence** - Database layer for users, API keys, sessions, routes, audit logs, tenants
- **Database Migrations** - Alembic for schema versioning
- **Backup & Recovery** - Automated database backup scripts with retention policies
- **Kubernetes Ready** - Complete K8s manifests with HPA, ingress, and health probes
- **CI/CD Pipeline** - GitHub Actions with testing, security scanning, and multi-stage deployment

## 📊 Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            API Gateway                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────┐   │
│  │ Request ID    │  │Authentication │  │ Multi-Tenancy │  │  Audit   │   │
│  │ Propagation   │  │ (JWT/SSO)     │  │   Middleware  │  │  Logging │   │
│  └───────────────┘  └───────────────┘  └───────────────┘  └──────────┘   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────┐   │
│  │  Rate Limit   │  │   Caching     │  │Circuit Breaker│  │  Admin   │   │
│  │   (Redis)     │  │   (Redis)     │  │   Pattern     │  │   API    │   │
│  └───────────────┘  └───────────────┘  └───────────────┘  └──────────┘   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                 │
│  │  Load         │  │  Service      │  │   Database    │                 │
│  │  Balancing    │  │  Discovery    │  │  (PostgreSQL) │                 │
│  └───────────────┘  └───────────────┘  └───────────────┘                 │
└────────────────────────────────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼────────────────────┐
           │                   │                    │
      ┌────▼────┐         ┌────▼────┐        ┌─────▼────┐
      │  User   │         │ Product │        │  Order   │
      │ Service │         │ Service │        │ Service  │
      └─────────┘         └─────────┘        └──────────┘
```

## 📁 Project Structure

```
api/
├── gateway/                      # API Gateway
│   ├── config/                   # Configuration
│   │   ├── settings.py           # Application settings
│   │   ├── secrets.py            # Vault integration
│   │   └── routes.yaml           # Route configuration
│   ├── core/                     # Core functionality
│   │   ├── router.py             # Request routing
│   │   ├── proxy.py              # HTTP proxying
│   │   └── middleware.py         # Middleware stack
│   ├── auth/                     # Authentication
│   │   ├── jwt_handler.py        # JWT tokens
│   │   ├── api_key.py            # API key validation
│   │   ├── oauth.py              # OAuth 2.0 flows
│   │   ├── session_manager.py    # Session management
│   │   ├── sso.py                # SSO providers
│   │   └── sso_endpoints.py      # SSO API
│   ├── security/                 # Security features
│   │   ├── rate_limiter.py       # Rate limiting
│   │   ├── cors.py               # CORS configuration
│   │   └── validator.py          # Request validation
│   ├── cache/                    # Caching
│   │   ├── redis_cache.py        # Redis caching
│   │   └── cache_strategy.py     # Cache strategies
│   ├── resilience/               # Resilience patterns
│   │   ├── circuit_breaker.py    # Circuit breaker
│   │   ├── retry.py              # Retry logic
│   │   └── timeout.py            # Timeout handling
│   ├── monitoring/               # Monitoring
│   │   ├── logger.py             # Structured logging
│   │   ├── metrics.py            # Prometheus metrics
│   │   └── tracer.py             # Distributed tracing
│   ├── database/                 # Database layer
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── connection.py         # Connection pooling
│   │   └── repositories.py       # Data access layer
│   ├── health/                   # Health checks
│   │   └── checks.py             # Health endpoints
│   ├── discovery/                # Service discovery
│   │   └── consul_client.py      # Consul integration
│   ├── loadbalancing/            # Load balancing
│   │   └── strategies.py         # LB strategies
│   ├── admin/                    # Admin API
│   │   └── api.py                # Management endpoints
│   ├── audit/                    # Audit logging
│   │   ├── logger.py             # Audit logger
│   │   └── middleware.py         # Audit middleware
│   ├── tenancy/                  # Multi-tenancy
│   │   └── middleware.py         # Tenant middleware
│   └── main.py                   # Main application
├── services/                     # Microservices
│   ├── user-service/
│   ├── product-service/
│   └── order-service/
├── shared/                       # Shared code
│   ├── models/
│   ├── utils/
│   └── exceptions/
├── tests/                        # Tests
│   ├── unit/
│   └── integration/
├── deploy/                       # Deployment
│   ├── docker/                   # Dockerfiles
│   ├── docker-compose.yml        # Local development
│   ├── kubernetes/               # K8s manifests
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── hpa.yaml
│   │   └── ingress.yaml
│   ├── prometheus.yml            # Prometheus config
│   └── prometheus-alerts.yml     # Alert rules
├── alembic/                      # Database migrations
│   ├── versions/
│   └── env.py
├── scripts/                      # Operational scripts
│   ├── migrate.sh                # Run migrations
│   ├── backup.sh                 # Database backup
│   └── restore.sh                # Database restore
├── .github/workflows/            # CI/CD
│   └── ci-cd.yaml                # GitHub Actions
├── requirements.txt
├── alembic.ini
├── .env.example
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized setup)
- PostgreSQL 15+ (for persistence)
- Redis (for caching and rate limiting)
- Optional: HashiCorp Vault (for secrets management)
- Optional: HashiCorp Consul (for service discovery)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd api
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Running with Docker Compose (Recommended)

```bash
cd deploy
docker-compose up -d
```

This will start:
- **API Gateway** on port 8000
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **User Service** on port 8001
- **Product Service** on port 8002
- **Order Service** on port 8003
- **Prometheus** on port 9090
- **Grafana** on port 3000

Optional services (uncomment in docker-compose.yml):
- **Vault** on port 8200
- **Consul** on port 8500

### Database Setup

Run migrations to create database schema:

```bash
./scripts/migrate.sh
```

Or manually:
```bash
alembic upgrade head
```

### Running Locally

1. **Start PostgreSQL and Redis**
```bash
# Using Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=gateway_password -e POSTGRES_DB=api_gateway postgres:15
docker run -d -p 6379:6379 redis:7-alpine
```

2. **Run migrations**
```bash
alembic upgrade head
```

3. **Start the API Gateway**
```bash
python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📖 Usage

### API Documentation

Once running, access interactive API documentation:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Health & Monitoring

#### Health Checks
```bash
# Liveness probe (simple alive check)
curl http://localhost:8000/health/live

# Readiness probe (ready to serve traffic)
curl http://localhost:8000/health/ready

# Comprehensive health (all dependencies)
curl http://localhost:8000/api/health
```

#### Metrics & Monitoring
```bash
# Prometheus metrics
curl http://localhost:8000/api/metrics

# Circuit breaker status
curl http://localhost:8000/api/circuit-breakers

# List all routes
curl http://localhost:8000/api/routes
```

### Authentication

#### JWT Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Use token
curl http://localhost:8000/api/users \
  -H "Authorization: Bearer <jwt-token>"
```

#### SSO Authentication
```bash
# List available SSO providers
curl http://localhost:8000/api/auth/sso/providers

# Initiate Google login (opens browser)
open "http://localhost:8000/api/auth/sso/google/login?redirect_uri=http://localhost:8000/callback"
```

#### API Key Authentication
```bash
# Create API key (requires auth)
curl -X POST http://localhost:8000/api/keys \
  -H "Authorization: Bearer <jwt-token>"

# Use API key
curl http://localhost:8000/api/products \
  -H "X-API-Key: <api-key>"
```

### Admin API

```bash
# Get current configuration
curl http://localhost:8000/admin/config

# Reload configuration
curl -X POST http://localhost:8000/admin/config/reload

# List all routes
curl http://localhost:8000/admin/routes

# Create new route (no restart needed!)
curl -X POST http://localhost:8000/admin/routes \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/v2/users",
    "methods": ["GET", "POST"],
    "upstream": "http://new-user-service:8080",
    "auth_required": true
  }'

# Reset circuit breaker
curl -X POST http://localhost:8000/admin/circuit-breakers/user-service/reset

# Clear cache by pattern
curl -X POST "http://localhost:8000/admin/cache/clear?pattern=users:*"
```

### Multi-Tenancy

```bash
# Request with tenant ID (via header)
curl http://localhost:8000/api/products \
  -H "X-Tenant-ID: tenant-123"

# Request with tenant ID (via subdomain)
curl http://tenant-123.localhost:8000/api/products
```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Application
DEBUG=false
ENVIRONMENT=production
APP_NAME=api-gateway
APP_VERSION=1.0.0

# Database (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=api_gateway
DB_USER=gateway_user
DB_PASSWORD=<secure-password>
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Security
SECRET_KEY=<generate-secure-key>
JWT_EXPIRATION_MINUTES=60
API_KEY_PREFIX=gw_

# Vault (optional)
VAULT_ENABLED=false
VAULT_URL=http://localhost:8200
VAULT_TOKEN=<vault-token>

# Consul (optional)
CONSUL_ENABLED=false
CONSUL_HOST=localhost
CONSUL_PORT=8500

# SSO (optional)
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
GITHUB_CLIENT_ID=<github-client-id>
GITHUB_CLIENT_SECRET=<github-client-secret>
AZURE_CLIENT_ID=<azure-client-id>
AZURE_CLIENT_SECRET=<azure-client-secret>
AZURE_TENANT_ID=common

# Feature Flags
RATE_LIMIT_ENABLED=true
CACHE_ENABLED=true
CIRCUIT_BREAKER_ENABLED=true
METRICS_ENABLED=true
TRACING_ENABLED=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Caching
CACHE_TTL_SECONDS=300

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60

# Logging
LOG_LEVEL=INFO
```

### Route Configuration

Routes are configured in `gateway/config/routes.yaml`:

```yaml
services:
  user-service:
    url: http://user-service:8001
    health_check: /health

  product-service:
    url: http://product-service:8002
    health_check: /health

routes:
  # User Service Routes
  - path: "/api/users"
    methods: ["GET", "POST"]
    service: "user-service"
    upstream: "http://user-service:8001"
    auth_required: true
    strip_path: false
    rate_limit:
      requests: 100
      window: 60
    cache:
      enabled: true
      ttl: 300

  # Product Service Routes
  - path: "/api/products"
    methods: ["GET"]
    service: "product-service"
    upstream: "http://product-service:8002"
    auth_required: false
    cache:
      enabled: true
      ttl: 600
```

## 🔒 Security Best Practices

1. **Change Default Secrets**
   - Generate strong `SECRET_KEY` (32+ characters)
   - Use secure database passwords
   - Rotate secrets regularly

2. **Enable HTTPS**
   - Use TLS certificates in production
   - Set `FORCE_HTTPS=true`
   - Configure proper certificate validation

3. **Authentication**
   - Implement strong password policies
   - Enable multi-factor authentication
   - Use short JWT expiration times

4. **Rate Limiting**
   - Set appropriate limits per endpoint
   - Use different limits for authenticated vs anonymous users
   - Monitor rate limit metrics

5. **CORS**
   - Don't use `*` in production
   - Whitelist specific origins
   - Review CORS settings regularly

6. **Database Security**
   - Use least-privilege database accounts
   - Enable SSL for database connections
   - Regular backups and disaster recovery testing

7. **Audit Logging**
   - Enable audit logging for compliance
   - Monitor audit logs for suspicious activity
   - Retain logs per compliance requirements

## 📊 Monitoring & Alerting

### Prometheus Metrics

The gateway exposes 25+ metrics:

- **Request Metrics**: `http_requests_total`, `http_request_duration_seconds`
- **Proxy Metrics**: `proxy_requests_total`, `proxy_errors_total`
- **Cache Metrics**: `cache_hits_total`, `cache_misses_total`
- **Circuit Breaker**: `circuit_breaker_state`, `circuit_breaker_transitions_total`
- **Rate Limiting**: `rate_limit_exceeded_total`
- **Database**: `db_connection_pool_active`, `db_connection_pool_size`

### Alerting Rules

Pre-configured alerts include:
- High error rate (>5% warning, >10% critical)
- High response time (p95 > 2s)
- Circuit breakers open
- Database pool exhaustion
- Redis connection failures
- SSL certificate expiry warnings

Access Prometheus: http://localhost:9090
Access Grafana: http://localhost:3000 (admin/admin)

## 🔄 Database Operations

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Show migration history
alembic history
```

### Backups

```bash
# Create backup
./scripts/backup.sh

# List available backups
./scripts/restore.sh

# Restore from latest backup
./scripts/restore.sh latest

# Restore from specific backup
./scripts/restore.sh backups/api_gateway_20240115_120000.sql.gz
```

Backups are stored in `backups/` with 30-day retention by default.

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Ingress controller (e.g., nginx-ingress)

### Deploy

```bash
# Create namespace
kubectl create namespace api-gateway

# Apply manifests
kubectl apply -f deploy/kubernetes/

# Check status
kubectl get pods -n api-gateway
kubectl get svc -n api-gateway
kubectl get hpa -n api-gateway
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment gateway -n api-gateway --replicas=5

# HPA auto-scales based on:
# - CPU utilization (>70%)
# - Memory utilization (>80%)
# - Min replicas: 3
# - Max replicas: 10
```

## 🔄 CI/CD Pipeline

The GitHub Actions pipeline includes:

1. **Lint & Test** - Code quality checks, unit tests
2. **Integration Tests** - Full stack with PostgreSQL and Redis
3. **Security Scan** - Trivy vulnerability scanner, TruffleHog secrets detection
4. **Build & Push** - Docker image to container registry
5. **Deploy Staging** - Auto-deploy to staging on main branch
6. **Deploy Production** - Manual approval for production on tags

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gateway --cov-report=html

# Run specific test file
pytest tests/unit/test_router.py

# Run integration tests (requires Docker)
pytest tests/integration/

# Generate coverage report
open htmlcov/index.html
```

## 🐛 Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Check database is running
docker ps | grep postgres

# Test connection
psql -h localhost -U gateway_user -d api_gateway

# Check migrations
alembic current
```

**Redis connection errors:**
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli ping

# Check Redis logs
docker logs api-gateway-redis
```

**Circuit breaker always open:**
```bash
# Check upstream service health
curl http://localhost:8001/health

# Reset circuit breaker
curl -X POST http://localhost:8000/admin/circuit-breakers/user-service/reset

# Monitor circuit breaker status
curl http://localhost:8000/api/circuit-breakers
```

**High memory usage:**
- Increase container memory limits
- Adjust connection pool sizes
- Review cache TTL settings
- Check for memory leaks in custom code

## 📈 Performance Tuning

1. **Workers** - Set `WORKERS` to 2× CPU cores
2. **Connection Pools** - Tune `DB_POOL_SIZE` based on concurrent requests
3. **Cache TTL** - Balance freshness vs performance
4. **Rate Limits** - Set appropriate limits per service tier
5. **Load Balancing** - Choose strategy based on workload:
   - `round_robin` - Simple, evenly distributed
   - `least_connections` - Better for varying request durations
   - `consistent_hashing` - Session affinity
   - `weighted` - Capacity-based distribution

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting guide

## 🎯 Roadmap

Completed features:
- ✅ Database persistence with PostgreSQL
- ✅ Database migrations with Alembic
- ✅ Health checks (Kubernetes-ready)
- ✅ Secrets management (Vault)
- ✅ Session management
- ✅ Request ID propagation
- ✅ Service discovery (Consul)
- ✅ Load balancing (5 strategies)
- ✅ Admin API
- ✅ Kubernetes manifests with HPA
- ✅ CI/CD pipeline
- ✅ Audit logging
- ✅ Multi-tenancy
- ✅ SSO authentication (Google, GitHub, Azure AD)
- ✅ Prometheus alerting rules
- ✅ Backup and recovery scripts

Future enhancements:
- [ ] WebSocket support
- [ ] GraphQL gateway
- [ ] gRPC protocol support
- [ ] Admin web UI
- [ ] API analytics dashboard
- [ ] Plugin system for extensibility
- [ ] Service mesh integration (Istio, Linkerd)
- [ ] Message queue support (Kafka, RabbitMQ)
