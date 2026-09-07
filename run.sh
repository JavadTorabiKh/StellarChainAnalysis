#!/bin/bash

echo "========================================="
echo "  Deploying ALL-IN-ONE Container"
echo "  Ubuntu 22.04 + Python 3.10"
echo "  PostgreSQL 14 + NumPy 1.24.3"
echo "  IP: "
echo "========================================="

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

if [ "$EUID" -ne 0 ]; then 
    error "Please run as root (use sudo)"
fi

log "Step 1: Configuring Docker..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://registry.docker.ir",
    "https://docker.iranserver.com",
    "https://hub.docker.ir"
  ],
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
EOF

systemctl restart docker
sleep 5
success "Docker configured"

log "Step 2: Cleaning everything..."
docker compose down -v 2>/dev/null
docker volume rm postgres_data 2>/dev/null
docker system prune -af 2>/dev/null
success "Cleaned"

log "Step 3: Creating directories..."
mkdir -p nginx/conf.d backups staticfiles media logs
chmod -R 755 staticfiles media logs
success "Directories created"


log "Step 5: Building and starting container..."
docker compose build --no-cache
docker compose up -d
success "Container started"


log "Step 6: Waiting for services (60 seconds)..."
for i in {1..60}; do
    echo -n "."
    sleep 1
done
echo ""

log "Step 7: Checking status..."
docker compose ps

log "Step 8: Recent logs..."
docker logs app --tail=50

log "Step 9: Testing NumPy installation..."
docker exec app python -c "import numpy; print(f'NumPy version: {numpy.__version__}')" 2>/dev/null


echo ""
echo "========================================="
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "========================================="
