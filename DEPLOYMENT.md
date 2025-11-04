# Deployment Guide - GovCon AI Pipeline

This guide covers deploying the GovCon AI Pipeline to production environments.

## Prerequisites

- Docker and Docker Compose
- Access to target environment (AWS, Azure, GCP, or on-prem)
- Domain name (for production)
- SSL certificates
- API keys (OpenAI/Anthropic, SAM.gov, BLS)

## Environment Setup

### Production Environment Variables

Create a production `.env` file:

```env
# Database
POSTGRES_URL=postgresql://user:password@postgres.internal:5432/govcon
POSTGRES_USER=govcon_prod
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=govcon_prod

# Redis
REDIS_URL=redis://:password@redis.internal:6379/0
REDIS_PASSWORD=<strong-password>

# API Keys
OPENAI_API_KEY=sk-...
SAM_GOV_API_KEY=...
BLS_API_KEY=...

# Security
JWT_SIGNING_KEY=<generate-strong-key>
SESSION_SECRET_KEY=<generate-strong-key>
ENCRYPTION_KEY=<32-byte-key>

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_LOG_LEVEL=info

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production

# Features
DEBUG=false
TESTING=false
REQUIRE_PINK_TEAM_APPROVAL=true
REQUIRE_GOLD_TEAM_APPROVAL=true
```

### Generate Secrets

```bash
# JWT signing key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption key (32 bytes)
python -c "import secrets; print(secrets.token_bytes(32).hex())"

# Database password
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

## Docker Compose Production

### 1. Production docker-compose.yml

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - internal

  qdrant:
    image: qdrant/qdrant:latest
    restart: always
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - internal

  minio:
    image: minio/minio:latest
    restart: always
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    networks:
      - internal

  api:
    build: .
    restart: always
    command: uvicorn govcon.api.main:app --host 0.0.0.0 --port 8000 --workers 4
    env_file: .env
    depends_on:
      - postgres
      - redis
      - qdrant
      - minio
    networks:
      - internal
      - external
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.api.tls=true"
      - "traefik.http.routers.api.tls.certresolver=letsencrypt"

  worker:
    build: .
    restart: always
    command: python -m govcon.worker
    env_file: .env
    depends_on:
      - postgres
      - redis
    networks:
      - internal

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    networks:
      - external

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  minio_data:

networks:
  internal:
    internal: true
  external:
```

### 2. Deploy

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Initialize database
docker-compose -f docker-compose.prod.yml exec api python -m govcon.cli init-db

# Check health
docker-compose -f docker-compose.prod.yml ps
```

## Kubernetes Deployment

### 1. Create Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: govcon-ai
```

### 2. Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: govcon-secrets
  namespace: govcon-ai
type: Opaque
stringData:
  postgres-password: <password>
  redis-password: <password>
  jwt-signing-key: <key>
  openai-api-key: <key>
```

### 3. PostgreSQL StatefulSet

```yaml
# postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: govcon-ai
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: govcon-secrets
              key: postgres-password
        - name: POSTGRES_DB
          value: govcon_prod
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: govcon-ai
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
```

### 4. API Deployment

```yaml
# api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: govcon-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: your-registry/govcon-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: POSTGRES_URL
          value: postgresql://postgres:5432/govcon_prod
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: govcon-secrets
              key: postgres-password
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: govcon-ai
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 5. Deploy to Kubernetes

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f postgres.yaml
kubectl apply -f api.yaml

# Check status
kubectl get pods -n govcon-ai

# View logs
kubectl logs -f deployment/api -n govcon-ai
```

## AWS Deployment

### Using ECS Fargate

1. **Create ECR Repository**

```bash
aws ecr create-repository --repository-name govcon-ai-pipeline

# Build and push image
docker build -t govcon-ai-pipeline .
docker tag govcon-ai-pipeline:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/govcon-ai-pipeline:latest
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/govcon-ai-pipeline:latest
```

2. **Create RDS PostgreSQL**

```bash
aws rds create-db-instance \
  --db-instance-identifier govcon-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16 \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 100 \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name default
```

3. **Create ECS Task Definition**

```json
{
  "family": "govcon-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/govcon-ai-pipeline:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "POSTGRES_URL",
          "value": "postgresql://admin:password@govcon-db.xxx.rds.amazonaws.com:5432/govcon"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:openai-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/govcon-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

4. **Create ECS Service**

```bash
aws ecs create-service \
  --cluster govcon-cluster \
  --service-name govcon-api \
  --task-definition govcon-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Monitoring

### Application Monitoring

```python
# Add to main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    environment=settings.sentry_environment,
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)
```

### Health Checks

Configure load balancer health checks:

- **Path**: `/health`
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Healthy threshold**: 2
- **Unhealthy threshold**: 3

### Log Aggregation

Use CloudWatch, Datadog, or ELK:

```yaml
# docker-compose.prod.yml - add logging
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Backup & Recovery

### Database Backups

```bash
# Manual backup
docker-compose exec postgres pg_dump -U govcon_prod govcon_prod > backup.sql

# Automated backups (cron)
0 2 * * * docker-compose exec postgres pg_dump -U govcon_prod govcon_prod | gzip > /backups/govcon_$(date +\%Y\%m\%d).sql.gz
```

### Object Storage Backups

Configure MinIO replication or use S3 versioning.

## Security Hardening

### 1. Network Security

- Use private networks for internal services
- Expose only API through load balancer
- Configure firewall rules
- Enable VPN for admin access

### 2. SSL/TLS

```bash
# Generate certificates
certbot certonly --standalone -d api.yourdomain.com
```

### 3. Database Security

- Use strong passwords
- Enable SSL connections
- Restrict network access
- Regular security updates

### 4. API Security

- Rate limiting
- CORS configuration
- JWT validation
- Input sanitization

## Scaling

### Horizontal Scaling

```bash
# Scale API replicas
docker-compose -f docker-compose.prod.yml up -d --scale api=5

# Kubernetes
kubectl scale deployment api --replicas=5 -n govcon-ai
```

### Vertical Scaling

Adjust resource limits in docker-compose or Kubernetes manifests.

### Database Scaling

- Read replicas for queries
- Connection pooling
- Query optimization

## Troubleshooting

### Check Logs

```bash
# Docker Compose
docker-compose logs -f api

# Kubernetes
kubectl logs -f deployment/api -n govcon-ai

# Specific container
docker logs <container-id>
```

### Database Connection Issues

```bash
# Test connection
docker-compose exec api python -c "from govcon.utils.database import engine; engine.connect()"
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check database queries
docker-compose exec postgres psql -U govcon_prod -c "SELECT * FROM pg_stat_activity;"
```

## Maintenance

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Rolling update
docker-compose -f docker-compose.prod.yml up -d
```

### Database Migrations

```bash
# Create migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

## Cost Optimization

### AWS Cost Optimization

- Use Spot Instances for workers
- Enable auto-scaling
- Right-size RDS instances
- Use S3 lifecycle policies

### General Tips

- Cache frequently accessed data
- Optimize database queries
- Use CDN for static assets
- Monitor and adjust resources

---

For additional help, see:
- [Architecture Documentation](ARCHITECTURE.md)
- [Quick Start Guide](QUICKSTART.md)
- [API Reference](API.md)
