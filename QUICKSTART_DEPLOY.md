# Quick Deploy Guide - Get Running in 15 Minutes

This is the fastest way to deploy GovCon AI Pipeline on a cost-optimized VPS.

**Total Cost: $18-25/month** | **Time: 15 minutes**

---

## Prerequisites Checklist

- [ ] VPS account (Hetzner, DigitalOcean, or Linode)
- [ ] Domain name (optional, but recommended)
- [ ] OpenAI API key
- [ ] SAM.gov API key
- [ ] Credit card (for VPS)

---

## Step 1: Get a VPS (2 minutes)

### Recommended: Hetzner Cloud

1. Go to https://hetzner.cloud
2. Sign up and verify account
3. Create new project: "govcon-prod"
4. Create server:
   - **Location**: Closest to you (e.g., Ashburn, VA)
   - **Image**: Ubuntu 22.04
   - **Type**: CPX31 (4 vCPU, 8GB RAM) - **$18/month**
   - **SSH Key**: Add your public key
5. Note the server IP address

---

## Step 2: Point Your Domain (1 minute)

If you have a domain, add these DNS records:

```
A    @                  -> YOUR_VPS_IP
A    www                -> YOUR_VPS_IP
A    api                -> YOUR_VPS_IP
```

Wait 2-5 minutes for DNS propagation.

**No domain?** You can still deploy using the IP address.

---

## Step 3: Initial Server Setup (3 minutes)

SSH into your VPS:

```bash
ssh root@YOUR_VPS_IP
```

Download and run the setup script:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/govcon-ai-pipeline/main/scripts/deploy-vps.sh -o setup.sh
chmod +x setup.sh
./setup.sh
```

This installs Docker, sets up firewall, creates swap, and optimizes the system.

---

## Step 4: Clone and Configure (3 minutes)

```bash
# Switch to deployment user
su - govcon

# Go to deployment directory
cd /opt/govcon-ai-pipeline

# Clone repository (replace with your repo URL)
git clone YOUR_REPO_URL .

# Copy environment template
cp .env.production .env

# Generate secure passwords
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))" >> .env
python3 -c "import secrets; print('JWT_SIGNING_KEY=' + secrets.token_urlsafe(32))" >> .env
python3 -c "import secrets; print('SESSION_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env
python3 -c "import secrets; print('MINIO_SECRET_KEY=' + secrets.token_urlsafe(24))" >> .env

# Edit .env and add your API keys
vim .env
```

**Required values to add:**
```bash
OPENAI_API_KEY=sk-proj-your_key_here
SAM_GOV_API_KEY=your_key_here
DOMAIN=yourdomain.com  # or use IP
API_DOMAIN=api.yourdomain.com
```

---

## Step 5: Configure Caddy (2 minutes)

Edit the Caddyfile:

```bash
vim Caddyfile
```

Replace `yourdomain.com` with your actual domain (3 places).

**Using IP only?** Replace the Caddyfile content with:

```caddyfile
http://:80 {
    reverse_proxy frontend:80
}

http://:8000 {
    reverse_proxy api:8000
}
```

---

## Step 6: Deploy! (4 minutes)

```bash
# Build and start services
docker compose -f docker-compose.prod.yml up -d

# Wait 30 seconds for services to start
sleep 30

# Initialize database
docker compose -f docker-compose.prod.yml exec api python -m govcon.cli init-db

# Check status
./scripts/manage.sh health
```

Expected output:
```
✓ API is healthy
✓ PostgreSQL is healthy
✓ Redis is healthy
```

---

## Step 7: Test (1 minute)

Open your browser:

- **Frontend**: https://yourdomain.com (or http://YOUR_VPS_IP)
- **API Docs**: https://api.yourdomain.com/docs

Test the API:
```bash
curl https://api.yourdomain.com/health
# Should return: {"status":"healthy"}
```

---

## You're Live! 🎉

Your GovCon AI Pipeline is now running in production.

---

## Quick Commands

Use the management script for easy operations:

```bash
# Check status
./scripts/manage.sh status

# View logs
./scripts/manage.sh logs

# Restart services
./scripts/manage.sh restart

# Create backup
./scripts/manage.sh backup

# Check health
./scripts/manage.sh health
```

---

## Next Steps

### Immediate (Required)
1. ✅ Set up automated backups:
   ```bash
   crontab -e
   # Add: 0 2 * * * /opt/govcon-ai-pipeline/scripts/manage.sh backup
   ```

2. ✅ Set up monitoring (free):
   - Sign up at https://uptimerobot.com
   - Monitor: https://api.yourdomain.com/health

### This Week (Recommended)
3. ✅ Migrate to Cloudflare R2 (saves $10-15/month):
   ```bash
   ./scripts/migrate-to-r2.sh
   ```

4. ✅ Set OpenAI billing alerts:
   - Go to https://platform.openai.com/settings/organization/billing/limits
   - Set monthly budget: $20-50

5. ✅ Secure SSH (disable password login):
   ```bash
   sudo vim /etc/ssh/sshd_config
   # Set: PasswordAuthentication no
   sudo systemctl restart sshd
   ```

### Later (Nice to Have)
6. ⏭️ Set up CI/CD with GitHub Actions
7. ⏭️ Configure error tracking with Sentry
8. ⏭️ Add custom email notifications

---

## Cost Breakdown

### Monthly Costs
- **VPS (Hetzner CPX31)**: $18/month
- **Domain**: $1/month (optional)
- **OpenAI API** (5M tokens/month): $3-5/month
- **Cloudflare R2** (after migration): $1/month
- **Total**: $23-25/month

### Cost Optimization Tips
1. Use `gpt-4o-mini` by default (90% cheaper)
2. Migrate to Cloudflare R2 (saves $10-15/month)
3. Enable caching (already configured)
4. Monitor API usage closely
5. Set billing alerts

---

## Troubleshooting

### Services won't start
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Restart
docker compose -f docker-compose.prod.yml restart
```

### Can't access via HTTPS
- Check DNS is pointing to VPS IP: `dig yourdomain.com`
- Check firewall: `sudo ufw status`
- Check Caddy logs: `docker compose -f docker-compose.prod.yml logs caddy`

### API returns 502
```bash
# Check API logs
./scripts/manage.sh logs-api

# Restart API
docker compose -f docker-compose.prod.yml restart api
```

### Out of memory
```bash
# Check memory usage
free -h

# Restart services to free memory
docker compose -f docker-compose.prod.yml restart
```

---

## Support

- **Full Guide**: [DEPLOY_VPS_GUIDE.md](DEPLOY_VPS_GUIDE.md)
- **R2 Migration**: [scripts/migrate-to-r2.sh](scripts/migrate-to-r2.sh)
- **Management**: [scripts/manage.sh](scripts/manage.sh)

---

## Security Checklist

- [ ] Changed all default passwords in `.env`
- [ ] Set up SSH key authentication
- [ ] Disabled SSH password login
- [ ] Configured firewall (UFW)
- [ ] Set up automated backups
- [ ] Configured monitoring
- [ ] Set API usage limits
- [ ] Reviewed environment variables

---

**Congrats! You're running a production-ready AI pipeline for ~$25/month** 🚀
