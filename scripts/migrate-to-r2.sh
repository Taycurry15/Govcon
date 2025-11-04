#!/bin/bash
set -e

# Cloudflare R2 Migration Script
# This script helps migrate from MinIO to Cloudflare R2 for cost savings
# R2 offers: 10GB free storage, zero egress fees, S3-compatible API

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cloudflare R2 Migration Guide${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${GREEN}Why Cloudflare R2?${NC}"
echo -e "• 10GB free storage (vs MinIO requiring VPS resources)"
echo -e "• Zero egress fees (save $0.09/GB on downloads)"
echo -e "• S3-compatible API (minimal code changes)"
echo -e "• Better reliability and no maintenance"
echo -e "• Estimated savings: $5-15/month on small VPS\n"

echo -e "${YELLOW}Prerequisites:${NC}"
echo -e "1. Cloudflare account (free)"
echo -e "2. R2 enabled (free tier available)"
echo -e "3. R2 API tokens created\n"

echo -e "${YELLOW}Step-by-step setup:${NC}\n"

echo -e "${GREEN}Step 1: Create R2 Bucket${NC}"
echo -e "1. Go to https://dash.cloudflare.com/"
echo -e "2. Navigate to R2 Object Storage"
echo -e "3. Click 'Create bucket'"
echo -e "4. Name it: govcon-artifacts"
echo -e "5. Choose a location (e.g., WNAM - Western North America)\n"

echo -e "${GREEN}Step 2: Generate API Tokens${NC}"
echo -e "1. Go to R2 > Manage R2 API Tokens"
echo -e "2. Click 'Create API Token'"
echo -e "3. Permissions: Object Read & Write"
echo -e "4. Save the Access Key ID and Secret Access Key\n"

echo -e "${GREEN}Step 3: Get Account ID${NC}"
echo -e "1. On R2 dashboard, find your Account ID"
echo -e "2. It's shown in the right sidebar\n"

echo -e "${GREEN}Step 4: Configure Public Access (Optional)${NC}"
echo -e "1. Go to your bucket settings"
echo -e "2. Enable 'Public access' if you need public URLs"
echo -e "3. Note the public bucket URL (e.g., https://pub-xxxxx.r2.dev)\n"

echo -e "${YELLOW}Configuration:${NC}\n"

cat << 'EOF'
Add these to your .env file:

# Cloudflare R2 Configuration
USE_CLOUDFLARE_R2=true
R2_ACCOUNT_ID=your_account_id_here
R2_ACCESS_KEY_ID=your_access_key_id_here
R2_SECRET_ACCESS_KEY=your_secret_access_key_here
R2_BUCKET_NAME=govcon-artifacts
R2_PUBLIC_BUCKET_URL=https://pub-xxxxx.r2.dev  # If using public access
R2_ENDPOINT=https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com

# Optional: Keep MinIO for local development
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=bronze
MINIO_SECRET_KEY=your_secret
MINIO_BUCKET=govcon-artifacts
EOF

echo -e "\n${YELLOW}Updating docker-compose:${NC}\n"

cat << 'EOF'
To save resources, you can remove MinIO from production:

# In docker-compose.prod.yml, comment out or remove:
# - minio service
# - minio-init service

Then remove from api dependencies:
  api:
    depends_on:
      - postgres
      - redis
      - qdrant
      # - minio  # Removed, using R2 instead
EOF

echo -e "\n${GREEN}Step 5: Migrate Existing Data${NC}\n"

echo -e "Install rclone for data migration:"
echo -e "${YELLOW}curl https://rclone.org/install.sh | sudo bash${NC}\n"

echo -e "Configure rclone for MinIO (source):"
cat << 'EOF'
rclone config create minio s3 \
  provider Minio \
  access_key_id YOUR_MINIO_KEY \
  secret_access_key YOUR_MINIO_SECRET \
  endpoint http://localhost:9000
EOF

echo -e "\nConfigure rclone for R2 (destination):"
cat << 'EOF'
rclone config create r2 s3 \
  provider Cloudflare \
  access_key_id YOUR_R2_ACCESS_KEY \
  secret_access_key YOUR_R2_SECRET_KEY \
  endpoint https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com \
  acl private
EOF

echo -e "\nCopy data from MinIO to R2:"
echo -e "${YELLOW}rclone copy minio:govcon-artifacts r2:govcon-artifacts -P${NC}\n"

echo -e "${GREEN}Step 6: Update Application Code${NC}\n"

cat << 'EOF'
The application needs minimal changes for R2 support.
S3-compatible clients work with R2 using boto3:

import boto3

if USE_CLOUDFLARE_R2:
    s3_client = boto3.client(
        's3',
        endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name='auto'  # R2 uses 'auto' as region
    )
else:
    # Use MinIO for local development
    s3_client = boto3.client('s3', endpoint_url=MINIO_ENDPOINT, ...)
EOF

echo -e "\n${GREEN}Step 7: Test and Deploy${NC}\n"

cat << 'EOF'
1. Test locally first:
   docker compose -f docker-compose.prod.yml up -d

2. Verify R2 connectivity:
   docker compose exec api python -c "from govcon.utils.storage import test_r2_connection; test_r2_connection()"

3. Upload a test file:
   docker compose exec api python -c "from govcon.utils.storage import upload_test; upload_test()"

4. If successful, deploy to production

5. Monitor for 24 hours, then remove MinIO if stable
EOF

echo -e "\n${YELLOW}Cost Comparison:${NC}\n"

cat << 'EOF'
Monthly costs for 50GB storage + 100GB egress:

MinIO (self-hosted):
  - VPS resources: ~$5-10/month (disk + memory)
  - Maintenance time: ~2 hours/month
  - Backup storage: ~$5/month
  Total: ~$10-15/month + time

Cloudflare R2:
  - Storage (50GB): $0.015/GB × 50 = $0.75/month
  - Class A operations (10k): $0.0036/1k × 10 = $0.036/month
  - Class B operations (100k): $0.00036/1k × 100 = $0.036/month
  - Egress: $0 (FREE!)
  Total: ~$0.82/month

Savings: ~$10-14/month = $120-168/year
EOF

echo -e "\n${GREEN}Additional R2 Features:${NC}"
echo -e "• Automatic backups and versioning"
echo -e "• No egress fees (huge savings)"
echo -e "• Better uptime than self-hosted"
echo -e "• No maintenance required"
echo -e "• Easy to scale"
echo -e "• S3-compatible (easy migration)\n"

echo -e "${YELLOW}Rollback Plan:${NC}"
echo -e "Keep MinIO configuration in .env for easy rollback:"
echo -e "${GREEN}USE_CLOUDFLARE_R2=false${NC}\n"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Migration guide complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "For questions, see: https://developers.cloudflare.com/r2/\n"
