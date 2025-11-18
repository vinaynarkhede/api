# API Gateway - Python Implementation

A modern, feature-rich API Gateway built with Python and FastAPI. This gateway provides routing, authentication, rate limiting, caching, circuit breaking, and comprehensive monitoring for microservices architectures.

## Features

### Core Features
- **Dynamic Request Routing** - Route requests to upstream services based on URL patterns
- **Load Balancing** - Distribute requests across multiple service instances
- **Service Discovery** - Dynamic service registration and discovery

### Security
- **JWT Authentication** - Secure token-based authentication
- **API Key Management** - API key generation and validation
- **OAuth 2.0 Support** - Password grant and client credentials flows
- **CORS Handling** - Cross-Origin Resource Sharing support
- **Request Validation** - SQL injection, XSS, and path traversal protection
- **Security Headers** - Automatic security header injection

### Performance & Reliability
- **Rate Limiting** - Token bucket and sliding window algorithms
- **Response Caching** - Redis-backed distributed caching
- **Circuit Breaker** - Prevent cascading failures
- **Retry Logic** - Exponential backoff for failed requests
- **Timeout Management** - Configurable timeouts for upstream requests

### Monitoring & Observability
- **Structured Logging** - JSON logging with structlog
- **Prometheus Metrics** - Comprehensive metrics collection
- **Distributed Tracing** - Request tracing across services
- **Health Checks** - Service health monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Authentication│  │ Rate Limiting│  │   Caching    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Circuit Breaker│  │   Routing    │  │  Monitoring  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
    │  User   │         │ Product │        │  Order  │
    │ Service │         │ Service │        │ Service │
    └─────────┘         └─────────┘        └─────────┘
```

## Project Structure

```
api/
├── gateway/                    # API Gateway
│   ├── config/                 # Configuration
│   │   ├── settings.py
│   │   └── routes.yaml
│   ├── core/                   # Core functionality
│   │   ├── router.py
│   │   ├── proxy.py
│   │   └── middleware.py
│   ├── auth/                   # Authentication
│   │   ├── jwt_handler.py
│   │   ├── api_key.py
│   │   └── oauth.py
│   ├── security/               # Security features
│   │   ├── rate_limiter.py
│   │   ├── cors.py
│   │   └── validator.py
│   ├── cache/                  # Caching
│   │   ├── redis_cache.py
│   │   └── cache_strategy.py
│   ├── resilience/             # Resilience patterns
│   │   ├── circuit_breaker.py
│   │   ├── retry.py
│   │   └── timeout.py
│   ├── monitoring/             # Monitoring
│   │   ├── logger.py
│   │   ├── metrics.py
│   │   └── tracer.py
│   └── main.py                 # Main application
├── services/                   # Microservices
│   ├── user-service/
│   ├── product-service/
│   └── order-service/
├── shared/                     # Shared code
│   ├── models/
│   ├── utils/
│   └── exceptions/
├── tests/                      # Tests
│   ├── unit/
│   └── integration/
├── deploy/                     # Deployment
│   ├── docker/
│   ├── docker-compose.yml
│   └── prometheus.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized setup)
- Redis (for caching and rate limiting)

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
- API Gateway on port 8000
- User Service on port 8001
- Product Service on port 8002
- Order Service on port 8003
- Redis on port 6379
- Prometheus on port 9090
- Grafana on port 3000

### Running Locally

1. **Start Redis**
```bash
redis-server
```

2. **Start the services**

Terminal 1 - User Service:
```bash
cd services/user-service
python main.py
```

Terminal 2 - Product Service:
```bash
cd services/product-service
python main.py
```

Terminal 3 - Order Service:
```bash
cd services/order-service
python main.py
```

Terminal 4 - API Gateway:
```bash
python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

### Accessing the Gateway

Once running, the API Gateway is available at `http://localhost:8000`

### API Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Available Endpoints

#### Gateway Management
- `GET /api/health` - Health check
- `GET /api/metrics` - Prometheus metrics
- `GET /api/routes` - List all routes
- `GET /api/circuit-breakers` - Circuit breaker status

#### User Service (via Gateway)
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/users` - List users (requires auth)
- `GET /api/users/{id}` - Get user (requires auth)
- `POST /api/users` - Create user (requires auth)
- `PUT /api/users/{id}` - Update user (requires auth)
- `DELETE /api/users/{id}` - Delete user (requires auth)

#### Product Service (via Gateway)
- `GET /api/products` - List products
- `GET /api/products/{id}` - Get product
- `POST /api/products` - Create product (requires auth)
- `PUT /api/products/{id}` - Update product (requires auth)
- `DELETE /api/products/{id}` - Delete product (requires auth)

#### Order Service (via Gateway)
- `GET /api/orders` - List orders (requires auth)
- `GET /api/orders/{id}` - Get order (requires auth)
- `POST /api/orders` - Create order (requires auth)
- `PUT /api/orders/{id}` - Update order (requires auth)
- `DELETE /api/orders/{id}` - Cancel order (requires auth)

### Example Requests

#### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

#### List Products (Public)
```bash
curl http://localhost:8000/api/products
```

#### List Users (Requires Authentication)
```bash
curl http://localhost:8000/api/users \
  -H "Authorization: Bearer <your-jwt-token>"
```

#### Create Order
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "items": [
      {"product_id": 1, "product_name": "Laptop", "quantity": 1, "price": 999.99}
    ],
    "shipping_address": "123 Main St"
  }'
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

Key settings:
- `SECRET_KEY` - JWT secret key (change in production!)
- `REDIS_HOST` - Redis host
- `RATE_LIMIT_ENABLED` - Enable/disable rate limiting
- `CACHE_ENABLED` - Enable/disable caching
- `CIRCUIT_BREAKER_ENABLED` - Enable/disable circuit breaker
- `METRICS_ENABLED` - Enable/disable metrics collection

### Route Configuration

Routes are configured in `gateway/config/routes.yaml`. Example:

```yaml
routes:
  - path: "/api/users"
    methods: ["GET", "POST"]
    service: "user-service"
    upstream: "http://user-service:8001"
    auth_required: true
    rate_limit:
      requests: 100
      window: 60
    cache:
      enabled: true
      ttl: 300
```

## Monitoring

### Metrics

Prometheus metrics are exposed at `/api/metrics`. Available metrics include:
- Request count and duration
- Proxy requests and errors
- Authentication attempts
- Rate limit hits
- Cache hits/misses
- Circuit breaker states

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (admin/admin) to visualize metrics.

### Logs

Structured JSON logs are written to stdout. In development, logs are formatted for console readability.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gateway --cov=services --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

## Security Considerations

1. **Change the SECRET_KEY** in production
2. **Use HTTPS** in production
3. **Implement proper user authentication** - The example uses mock authentication
4. **Store API keys securely** - Use a database with encryption
5. **Set appropriate rate limits** based on your use case
6. **Review CORS settings** - Don't use `*` in production
7. **Enable security headers** - Already configured
8. **Regular security audits** - Keep dependencies updated

## Performance Tuning

1. **Adjust worker count** - Set `WORKERS` based on CPU cores
2. **Tune rate limits** - Adjust per your traffic patterns
3. **Configure cache TTL** - Balance freshness vs performance
4. **Circuit breaker thresholds** - Set based on service reliability
5. **Connection pooling** - Already configured in HTTPProxy
6. **Redis optimization** - Consider Redis Cluster for high traffic

## Troubleshooting

### Common Issues

**Services can't connect:**
- Ensure all services are running
- Check Docker network connectivity
- Verify service URLs in `routes.yaml`

**Redis connection errors:**
- Ensure Redis is running
- Check `REDIS_HOST` and `REDIS_PORT`
- Verify network connectivity

**Rate limiting not working:**
- Ensure `RATE_LIMIT_ENABLED=true`
- Check Redis connectivity
- Verify rate limit configuration

**Circuit breaker always open:**
- Check upstream service health
- Review failure threshold settings
- Monitor circuit breaker status at `/api/circuit-breakers`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Related Projects

This API Gateway works with:
- Any FastAPI or Flask microservice
- REST APIs
- GraphQL services (with additional configuration)
- gRPC services (with protocol translation)

## Roadmap

- [ ] WebSocket support
- [ ] GraphQL gateway
- [ ] Service mesh integration
- [ ] Advanced load balancing strategies
- [ ] API analytics dashboard
- [ ] Multi-tenancy support
- [ ] Plugin system
- [ ] Admin UI

## Support

For issues, questions, or contributions, please open an issue on GitHub.
