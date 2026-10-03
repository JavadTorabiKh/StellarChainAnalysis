#!/bin/bash

echo "========================================="
echo "  Deploying Django ALL-IN-ONE Container"
echo "  Ubuntu 22.04 + Python 3.10"
echo "  PostgreSQL 14 + NumPy 1.24.3"
echo "  IP: dastyar.daneshbonyan.ir"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; exit 1; }
warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

if [ "$EUID" -ne 0 ]; then 
    error "Please run as root (use sudo)"
fi

# ============================================
# Function: Restart Docker (supports both Snap and standard)
# ============================================
restart_docker() {
    log "Restarting Docker service..."
    
    if systemctl list-units --full -all | grep -q "snap.docker.dockerd.service"; then
        warning "Detected Docker installation via Snap"
        sudo systemctl restart snap.docker.dockerd.service
        sleep 3
        if systemctl is-active --quiet snap.docker.dockerd.service; then
            success "Docker (Snap) restarted successfully"
            return 0
        else
            error "Failed to restart Docker (Snap)"
        fi
    elif systemctl list-units --full -all | grep -q "docker.service"; then
        warning "Detected standard Docker installation"
        sudo systemctl restart docker.service
        sleep 3
        if systemctl is-active --quiet docker.service; then
            success "Docker (standard) restarted successfully"
            return 0
        else
            error "Failed to restart Docker (standard)"
        fi
    else
        error "Docker service not found! Please install Docker first."
    fi
}

# ============================================
# Function: Configure Docker registry mirrors (supports both Snap and standard)
# ============================================
configure_docker_mirrors() {
    log "Configuring Docker registry mirrors..."
    
    if systemctl list-units --full -all | grep -q "snap.docker.dockerd.service"; then
        # Snap Docker configuration path
        DOCKER_CONFIG_PATH="/var/snap/docker/current/config/daemon.json"
        warning "Detected Snap Docker, using: $DOCKER_CONFIG_PATH"
    else
        # Standard Docker configuration path
        DOCKER_CONFIG_PATH="/etc/docker/daemon.json"
    fi
    
    # Create directory if it doesn't exist
    mkdir -p "$(dirname "$DOCKER_CONFIG_PATH")"
    
    # Write configuration
    cat > "$DOCKER_CONFIG_PATH" <<EOF
{
  "registry-mirrors": [
    "https://registry.docker.ir",
    "https://docker.iranserver.com",
    "https://hub.docker.ir"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    
    success "Docker mirrors configured at: $DOCKER_CONFIG_PATH"
    restart_docker
}

# ============================================
# Function: Check if Docker is running
# ============================================
check_docker() {
    log "Checking Docker status..."
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker first."
    fi
    success "Docker is running"
}

# ============================================
# 0. Install required tools
# ============================================
log "Step 0: Installing required tools..."
apt-get update -qq
apt-get install -y openssl curl -qq
success "Tools installed"

# ============================================
# 1. Configure Docker
# ============================================
configure_docker_mirrors
check_docker

# ============================================
# 2. Clean everything
# ============================================
log "Step 2: Cleaning everything..."
docker compose down -v 2>/dev/null
docker volume prune -f 2>/dev/null
docker system prune -af 2>/dev/null
success "Cleaned"

# ============================================
# 3. Create directories
# ============================================
log "Step 3: Creating directories..."
mkdir -p nginx/conf.d backups staticfiles media logs
chmod -R 755 staticfiles media logs
success "Directories created"

# ============================================
# 4. Copy main support.conf file
# ============================================
log "Step 4: Setting up main config..."

cat > nginx/conf.d/stellar.conf <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name ;

    client_max_body_size 100M;

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /app/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF



# ============================================
# 6. Build and start
# ============================================
log "Step 6: Building and starting container..."

# Try to pull image with retry
MAX_RETRIES=3
RETRY_COUNT=0
BUILD_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$BUILD_SUCCESS" = false ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log "Build attempt $RETRY_COUNT of $MAX_RETRIES..."
    
    if docker compose build --no-cache 2>&1 | tee /tmp/build.log; then
        BUILD_SUCCESS=true
        success "Build successful!"
    else
        warning "Build failed (attempt $RETRY_COUNT)"
        if grep -q "403 Forbidden" /tmp/build.log; then
            warning "Docker registry access issue detected. Retrying with mirror..."
            # Try with specific mirror
            docker pull docker.iranserver.com/library/ubuntu:22.04 2>/dev/null && \
            docker tag docker.iranserver.com/library/ubuntu:22.04 ubuntu:22.04 2>/dev/null
        fi
        sleep 5
    fi
done

if [ "$BUILD_SUCCESS" = false ]; then
    error "Failed to build container after $MAX_RETRIES attempts"
fi

docker compose up -d
success "Container started"

# ============================================
# 7. Wait for services
# ============================================
log "Step 7: Waiting for services (60 seconds)..."
for i in {1..60}; do
    echo -n "."
    sleep 1
done
echo ""

# ============================================
# 8. Check containers
# ============================================
log "Step 8: Checking status..."
docker compose ps

# ============================================
# 9. View logs
# ============================================
log "Step 9: Recent logs..."
if docker ps --format '{{.Names}}' | grep -q "support_app"; then
    docker logs support_app --tail=50
else
    warning "support_app container not found, showing all logs:"
    docker compose logs --tail=50
fi

# ============================================
# 10. Test NumPy
# ============================================
log "Step 10: Testing NumPy installation..."
CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -E 'support|app' | head -1)
if [ -n "$CONTAINER_NAME" ]; then
    docker exec "$CONTAINER_NAME" python -c "import numpy; print(f'NumPy version: {numpy.__version__}')" 2>/dev/null
    if [ $? -eq 0 ]; then
        success "NumPy is working!"
    else
        warning "NumPy test failed (might be installed in different container)"
    fi
else
    warning "No container found for NumPy test"
fi
