#!/bin/bash

# GovCon AI Pipeline - Management Script
# Quick commands for managing your production deployment

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.prod.yml"

show_help() {
    echo -e "${BLUE}GovCon AI Pipeline - Management Script${NC}\n"
    echo "Usage: ./manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       - Start all services"
    echo "  stop        - Stop all services"
    echo "  restart     - Restart all services"
    echo "  status      - Show service status"
    echo "  logs        - Show logs (all services)"
    echo "  logs-api    - Show API logs"
    echo "  logs-db     - Show database logs"
    echo "  health      - Check service health"
    echo "  stats       - Show resource usage"
    echo "  backup      - Create backup now"
    echo "  update      - Update and redeploy"
    echo "  clean       - Clean up Docker resources"
    echo "  shell       - Open shell in API container"
    echo "  db-shell    - Open PostgreSQL shell"
    echo ""
}

start() {
    echo -e "${YELLOW}Starting services...${NC}"
    docker compose -f $COMPOSE_FILE up -d
    echo -e "${GREEN}✓ Services started${NC}"
    status
}

stop() {
    echo -e "${YELLOW}Stopping services...${NC}"
    docker compose -f $COMPOSE_FILE down
    echo -e "${GREEN}✓ Services stopped${NC}"
}

restart() {
    echo -e "${YELLOW}Restarting services...${NC}"
    docker compose -f $COMPOSE_FILE restart
    echo -e "${GREEN}✓ Services restarted${NC}"
    status
}

status() {
    echo -e "${YELLOW}Service status:${NC}"
    docker compose -f $COMPOSE_FILE ps
}

logs() {
    echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    docker compose -f $COMPOSE_FILE logs -f --tail=100
}

logs_api() {
    echo -e "${YELLOW}Showing API logs (Ctrl+C to exit)...${NC}"
    docker compose -f $COMPOSE_FILE logs -f --tail=100 api
}

logs_db() {
    echo -e "${YELLOW}Showing database logs (Ctrl+C to exit)...${NC}"
    docker compose -f $COMPOSE_FILE logs -f --tail=100 postgres
}

health() {
    echo -e "${YELLOW}Checking health...${NC}\n"

    # Check API
    if curl -sf http://localhost:8000/health > /dev/null; then
        echo -e "${GREEN}✓ API is healthy${NC}"
    else
        echo -e "${RED}✗ API is unhealthy${NC}"
    fi

    # Check Postgres
    if docker compose -f $COMPOSE_FILE exec -T postgres pg_isready > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is healthy${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is unhealthy${NC}"
    fi

    # Check Redis
    if docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is healthy${NC}"
    else
        echo -e "${RED}✗ Redis is unhealthy${NC}"
    fi

    # Check disk space
    echo -e "\n${YELLOW}Disk usage:${NC}"
    df -h / | tail -1 | awk '{print "Used: " $3 " / " $2 " (" $5 ")"}'

    # Check memory
    echo -e "\n${YELLOW}Memory usage:${NC}"
    free -h | grep Mem | awk '{print "Used: " $3 " / " $2}'
}

stats() {
    echo -e "${YELLOW}Resource usage (Ctrl+C to exit):${NC}"
    docker stats
}

backup() {
    echo -e "${YELLOW}Creating backup...${NC}"

    BACKUP_DIR="/opt/backups"
    mkdir -p $BACKUP_DIR
    DATE=$(date +%Y%m%d_%H%M%S)

    # Backup database
    echo "Backing up database..."
    docker compose -f $COMPOSE_FILE exec -T postgres \
        pg_dump -U bronze govcon | gzip > $BACKUP_DIR/db_$DATE.sql.gz

    # Backup .env
    echo "Backing up configuration..."
    cp .env $BACKUP_DIR/env_$DATE

    echo -e "${GREEN}✓ Backup created: $DATE${NC}"
    ls -lh $BACKUP_DIR/*$DATE*
}

update() {
    echo -e "${YELLOW}Updating application...${NC}"

    # Backup first
    backup

    # Pull latest code
    echo -e "\n${YELLOW}Pulling latest code...${NC}"
    git pull origin main

    # Rebuild images
    echo -e "\n${YELLOW}Rebuilding images...${NC}"
    docker compose -f $COMPOSE_FILE build

    # Restart services
    echo -e "\n${YELLOW}Restarting services...${NC}"
    docker compose -f $COMPOSE_FILE up -d

    # Wait for health
    echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
    sleep 10

    # Check health
    health

    echo -e "\n${GREEN}✓ Update complete${NC}"
}

clean() {
    echo -e "${YELLOW}Cleaning Docker resources...${NC}"

    echo "Removing unused images..."
    docker image prune -a -f

    echo "Removing unused networks..."
    docker network prune -f

    echo "Removing build cache..."
    docker builder prune -f

    echo -e "${GREEN}✓ Cleanup complete${NC}"

    echo -e "\n${YELLOW}Disk space after cleanup:${NC}"
    df -h /
}

shell() {
    echo -e "${YELLOW}Opening shell in API container...${NC}"
    docker compose -f $COMPOSE_FILE exec api /bin/bash
}

db_shell() {
    echo -e "${YELLOW}Opening PostgreSQL shell...${NC}"
    docker compose -f $COMPOSE_FILE exec postgres psql -U bronze -d govcon
}

# Main command handler
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    logs-api)
        logs_api
        ;;
    logs-db)
        logs_db
        ;;
    health)
        health
        ;;
    stats)
        stats
        ;;
    backup)
        backup
        ;;
    update)
        update
        ;;
    clean)
        clean
        ;;
    shell)
        shell
        ;;
    db-shell)
        db_shell
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}\n"
        show_help
        exit 1
        ;;
esac
