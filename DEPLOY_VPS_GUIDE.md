# Cost-Optimized VPS Deployment Guide

Complete guide for deploying GovCon AI Pipeline on a budget VPS (Hetzner, DigitalOcean, Linode).

**Target Cost: $20-40/month**

## Table of Contents

1. [VPS Provider Selection](#vps-provider-selection)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Deployment](#deployment)
5. [Post-Deployment](#post-deployment)
6. [Cost Optimizations](#cost-optimizations)
7. [Monitoring](#monitoring)
8. [Backup Strategy](#backup-strategy)
9. [Troubleshooting](#troubleshooting)

---

## VPS Provider Selection

### Recommended Providers (4GB RAM, 2 vCPU)

| Provider | Plan | Cost/Month | Notes |
|----------|------|------------|-------|
| **Hetzner** | CPX21 | €9.00 (~$10) | Best value, excellent performance |
| Hetzner | CPX31 | €16.50 (~$18) | 4 vCPU, 8GB RAM (recommended) |
| DigitalOcean | Basic 4GB | $48 | Easy to use, good docs |
| Linode | Linode 4GB | $36 | Good support |
| Vultr | 4GB | $24 | Multiple locations |

**Recommendation**: Hetzner CPX31 (8GB RAM) for best price/performance.

### Minimum Requirements

- **CPU**: 2+ vCPUs
- **RAM**: 4GB (8GB recommended)
- **Storage**: 80GB SSD
- **Network**: 20TB+ bandwidth
- **OS**: Ubuntu 22.04 LTS (recommended)

---

## Initial Setup

### Step 1: Create VPS

1. Sign up with your chosen provider
2. Create a new VPS:
   - **OS**: Ubuntu 22.04 LTS
   - **Location**: Choose closest to your users
   - **SSH Key**: Add your public SSH key
   - **Hostname**: govcon-prod

3. Note down your VPS IP address

### Step 2: Configure Domain (Optional but Recommended)

If you have a domain:

1. Add A records pointing to your VPS IP:
   ```
   A    yourdomain.com          -> YOUR_VPS_IP
   A    www.yourdomain.com      -> YOUR_VPS_IP
   A    api.yourdomain.com      -> YOUR_VPS_IP
   A    minio.yourdomain.com    -> YOUR_VPS_IP  (optional)
   ```

2. Wait for DNS propagation (~5-30 minutes)

### Step 3: Initial Server Setup

SSH into your server:

```bash
ssh root@YOUR_VPS_IP
```

Run the automated setup script:

```bash
# Download and run the VPS setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/scripts/deploy-vps.sh -o deploy-vps.sh
chmod +x deploy-vps.sh
sudo ./deploy-vps.sh
```

Or manually run the script if you already have the repository.

This script will:
- ✅ Update system packages
- ✅ Install Docker and Docker Compose
- ✅ Configure firewall (UFW)
- ✅ Set up fail2ban
- ✅ Create swap file (helps with memory)
- ✅ Optimize system parameters
- ✅ Create deployment user

---

## Configuration

### Step 1: Clone Repository

```bash
# Switch to deployment user
su - govcon

# Create deployment directory
cd /opt/govcon-ai-pipeline

# Clone your repository
git clone YOUR_REPO_URL .
```

### Step 2: Configure Environment

```bash
# Copy production environment template
cp .env.production .env

# Edit with your values
vim .env
```

**Required Configuration:**

```bash
# 1. Database - Generate strong password
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

# 2. Security keys
JWT_SIGNING_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
SESSION_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 3. AI API Keys
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE

# 4. External APIs
SAM_GOV_API_KEY=your_key_here
BLS_API_KEY=your_key_here

# 5. Domain configuration
DOMAIN=yourdomain.com
API_DOMAIN=api.yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
```

### Step 3: Update Caddyfile

```bash
vim Caddyfile
```

Replace all instances of `yourdomain.com` with your actual domain:

```caddyfile
{
    email admin@yourdomain.com
}

yourdomain.com, www.yourdomain.com {
    reverse_proxy frontend:80
    # ... rest of config
}

api.yourdomain.com {
    reverse_proxy api:8000
    # ... rest of config
}
```

If you don't have a domain, use IP-based configuration:

```caddyfile
http://YOUR_VPS_IP {
    reverse_proxy frontend:80
}

http://YOUR_VPS_IP:8000 {
    reverse_proxy api:8000
}
```

---

## Deployment

### Step 1: Build and Start Services

```bash
# Build images (first time only)
docker compose -f docker-compose.prod.yml build

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

Expected output:
```
NAME                  STATUS    PORTS
govcon-api            healthy   8000/tcp
govcon-caddy          running   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
govcon-frontend       running   80/tcp
govcon-minio          healthy   9000-9001/tcp
govcon-postgres       healthy   5432/tcp
govcon-qdrant         running   6333-6334/tcp
govcon-redis          healthy   6379/tcp
```

### Step 2: Initialize Database

```bash
# Wait for services to be healthy (30-60 seconds)
docker compose -f docker-compose.prod.yml exec api python -m govcon.cli init-db
```

### Step 3: Test Deployment

```bash
# Test API health
curl http://localhost:8000/health

# Or if using domain
curl https://api.yourdomain.com/health

# Expected response: {"status": "healthy"}
```

### Step 4: Access the Application

- **Frontend**: https://yourdomain.com (or http://YOUR_VPS_IP)
- **API**: https://api.yourdomain.com (or http://YOUR_VPS_IP:8000)
- **API Docs**: https://api.yourdomain.com/docs

---

## Post-Deployment

### Secure SSH Access

```bash
# On your VPS as root
vim /etc/ssh/sshd_config
```

Update these settings:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

Restart SSH:
```bash
systemctl restart sshd
```

### Set Up Automated Backups

Create backup script:

```bash
vim /opt/govcon-ai-pipeline/scripts/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U bronze govcon | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup volumes
docker run --rm \
  -v govcon-ai-pipeline_postgres_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/volumes_$DATE.tar.gz /data

# Keep only last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
chmod +x /opt/govcon-ai-pipeline/scripts/backup.sh
crontab -e
# Add: 0 2 * * * /opt/govcon-ai-pipeline/scripts/backup.sh
```

---

## Cost Optimizations

### 1. Use GPT-4o-mini by Default

In your `.env`:
```bash
DEFAULT_MODEL=gpt-4o-mini  # ~90% cheaper than GPT-4
```

**Cost comparison (per 1M tokens):**
- GPT-4o: ~$2.50-$10.00
- GPT-4o-mini: ~$0.15-$0.60
- **Savings: ~$2.35-$9.40 per 1M tokens**

### 2. Migrate to Cloudflare R2

Replace MinIO with Cloudflare R2 (free tier):

```bash
# See detailed guide
./scripts/migrate-to-r2.sh
```

**Savings**: $5-15/month on VPS resources

### 3. Enable Aggressive Caching

Already configured in Redis with LRU eviction:
```yaml
redis:
  command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
```

### 4. Resource Limits

All services have memory limits in `docker-compose.prod.yml`:
- **postgres**: 512MB
- **redis**: 128MB
- **qdrant**: 512MB
- **api**: 1GB
- **Total**: ~2.2GB (fits in 4GB VPS)

### 5. Disable Ollama in Production

In `.env`:
```bash
USE_LOCAL_LLM=false
# OLLAMA_HOST commented out
```

**Savings**: ~1-2GB RAM, faster startup

### 6. Monitor API Usage

Set up OpenAI billing alerts:
1. Go to https://platform.openai.com/settings/organization/billing/limits
2. Set monthly budget: $20-50
3. Enable email notifications

---

## Monitoring

### Quick Health Check

```bash
# Check all services
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f --tail=50

# Check resource usage
docker stats

# Check disk space
df -h

# Check memory
free -h
```

### Set Up Uptime Monitoring (Free)

**UptimeRobot** (free for 50 monitors):
1. Sign up at https://uptimerobot.com
2. Add HTTP monitor: https://api.yourdomain.com/health
3. Set check interval: 5 minutes
4. Configure email alerts

**BetterUptime** (alternative, free tier):
- https://betteruptime.com
- More features, beautiful status pages

### Application Logs

```bash
# API logs
docker compose -f docker-compose.prod.yml logs -f api

# Database logs
docker compose -f docker-compose.prod.yml logs -f postgres

# All logs
docker compose -f docker-compose.prod.yml logs -f
```

---

## Backup Strategy

### Automated Daily Backups

Already configured in post-deployment. Backups include:
- Database dump (compressed)
- Docker volumes
- Configuration files

### Off-site Backup (Recommended)

Use Cloudflare R2 or AWS S3 for off-site backups:

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure R2
rclone config

# Sync backups to R2
rclone sync /opt/backups r2:govcon-backups
```

Add to crontab:
```bash
0 3 * * * rclone sync /opt/backups r2:govcon-backups
```

**Cost**: Free (within R2 free tier)

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs SERVICE_NAME

# Check container status
docker compose -f docker-compose.prod.yml ps

# Restart service
docker compose -f docker-compose.prod.yml restart SERVICE_NAME
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Restart services to clear memory
docker compose -f docker-compose.prod.yml restart
```

### Database Connection Issues

```bash
# Check postgres is healthy
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Test connection from API
docker compose -f docker-compose.prod.yml exec api \
  python -c "from govcon.utils.database import engine; engine.connect()"
```

### SSL Certificate Issues

```bash
# Check Caddy logs
docker compose -f docker-compose.prod.yml logs caddy

# Common issues:
# - Domain not pointing to VPS IP
# - Port 80/443 blocked by firewall
# - DNS not propagated yet
```

### High API Costs

```bash
# Check usage in OpenAI dashboard
# Enable caching for repeated requests
# Use gpt-4o-mini for non-critical tasks
# Set up request rate limiting
```

---

## Maintenance

### Updates

```bash
# Pull latest code
cd /opt/govcon-ai-pipeline
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check health
docker compose -f docker-compose.prod.yml ps
```

### Database Migrations

```bash
# If you're using Alembic
docker compose -f docker-compose.prod.yml exec api \
  alembic upgrade head
```

### Clean Up Docker

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (careful!)
docker volume prune

# Remove unused networks
docker network prune
```

---

## Monthly Cost Breakdown

### Base Infrastructure
- **Hetzner CPX31 VPS**: $18/month
- **Domain**: $1/month (Cloudflare)
- **Total Infrastructure**: $19/month

### Variable Costs (based on usage)
- **OpenAI API** (est. 5M tokens/month with GPT-4o-mini): $3-5/month
- **Cloudflare R2** (50GB storage): $1/month
- **Total Variable**: $4-6/month

### **Total Monthly Cost: $23-25/month**

### Cost at Scale
- 10M tokens: ~$28-30/month
- 50M tokens: ~$45-60/month
- 100M tokens: ~$80-100/month

---

## Support

- **Documentation**: [README.md](README.md)
- **Issues**: GitHub Issues
- **Hetzner Docs**: https://docs.hetzner.com/
- **Docker Docs**: https://docs.docker.com/
- **Caddy Docs**: https://caddyserver.com/docs/

---

## Next Steps

1. ✅ Deploy application
2. ✅ Set up monitoring
3. ✅ Configure backups
4. ⏭️ Migrate to Cloudflare R2 (see [scripts/migrate-to-r2.sh](scripts/migrate-to-r2.sh))
5. ⏭️ Set up CI/CD (GitHub Actions)
6. ⏭️ Configure error tracking (Sentry)
7. ⏭️ Optimize AI model usage

---

**Built with cost-efficiency in mind** | **Production-ready** | **Easy to maintain**
