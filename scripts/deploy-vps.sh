#!/bin/bash
set -e

# GovCon AI Pipeline - VPS Deployment Script
# For Ubuntu 22.04 LTS or Debian 12

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GovCon AI Pipeline - VPS Deployment${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

# Install required packages
echo -e "${YELLOW}Installing required packages...${NC}"
apt-get install -y \
    curl \
    git \
    wget \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    htop \
    vim

# Install Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Installing Docker...${NC}"

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Enable Docker service
    systemctl enable docker
    systemctl start docker

    echo -e "${GREEN}✓ Docker installed successfully${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Configure UFW firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
echo -e "${GREEN}✓ Firewall configured${NC}"

# Configure fail2ban
echo -e "${YELLOW}Configuring fail2ban...${NC}"
systemctl enable fail2ban
systemctl start fail2ban
echo -e "${GREEN}✓ Fail2ban configured${NC}"

# Create deployment directory
DEPLOY_DIR="/opt/govcon-ai-pipeline"
echo -e "${YELLOW}Creating deployment directory at ${DEPLOY_DIR}...${NC}"
mkdir -p $DEPLOY_DIR

# Set up Docker log rotation
echo -e "${YELLOW}Configuring Docker log rotation...${NC}"
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker
echo -e "${GREEN}✓ Docker log rotation configured${NC}"

# Create swap file if not exists (helps with memory on small VPS)
if [ ! -f /swapfile ]; then
    echo -e "${YELLOW}Creating 2GB swap file...${NC}"
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}✓ Swap file created${NC}"
else
    echo -e "${GREEN}✓ Swap file already exists${NC}"
fi

# Optimize sysctl for production
echo -e "${YELLOW}Optimizing system parameters...${NC}"
cat >> /etc/sysctl.conf <<EOF

# GovCon AI Pipeline optimizations
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.somaxconn=1024
net.ipv4.tcp_max_syn_backlog=2048
EOF
sysctl -p
echo -e "${GREEN}✓ System parameters optimized${NC}"

# Create a non-root user for deployment (if doesn't exist)
if ! id -u govcon &>/dev/null; then
    echo -e "${YELLOW}Creating govcon user...${NC}"
    useradd -m -s /bin/bash govcon
    usermod -aG docker govcon
    echo -e "${GREEN}✓ User 'govcon' created${NC}"
else
    echo -e "${GREEN}✓ User 'govcon' already exists${NC}"
fi

# Set ownership
chown -R govcon:govcon $DEPLOY_DIR

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}VPS Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Clone your repository to ${DEPLOY_DIR}"
echo -e "   ${GREEN}su - govcon${NC}"
echo -e "   ${GREEN}cd ${DEPLOY_DIR}${NC}"
echo -e "   ${GREEN}git clone <your-repo-url> .${NC}\n"

echo -e "2. Configure environment variables"
echo -e "   ${GREEN}cp .env.example .env${NC}"
echo -e "   ${GREEN}vim .env${NC}\n"

echo -e "3. Update Caddyfile with your domain"
echo -e "   ${GREEN}vim Caddyfile${NC}\n"

echo -e "4. Deploy the application"
echo -e "   ${GREEN}docker compose -f docker-compose.prod.yml up -d${NC}\n"

echo -e "5. Check status"
echo -e "   ${GREEN}docker compose -f docker-compose.prod.yml ps${NC}\n"

echo -e "${YELLOW}Security Reminders:${NC}"
echo -e "- Change default passwords in .env"
echo -e "- Set up SSH key authentication"
echo -e "- Disable password SSH login"
echo -e "- Configure automated backups"
echo -e "- Set up monitoring"

echo -e "\n${GREEN}Deployment script completed successfully!${NC}\n"
