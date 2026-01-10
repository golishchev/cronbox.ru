#!/bin/bash
# CronBox Server Setup Script
# Run this on a fresh Ubuntu/Debian server

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[SETUP]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

log "Updating system packages..."
apt-get update && apt-get upgrade -y

log "Installing required packages..."
apt-get install -y git curl

log "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

log "Installing Docker Compose plugin..."
apt-get install -y docker-compose-plugin

log "Creating cronbox user..."
if ! id "cronbox" &>/dev/null; then
    useradd -r -s /bin/bash -m -d /opt/cronbox cronbox
    usermod -aG docker cronbox
fi

log "Setting up application directory..."
APP_DIR=/opt/cronbox
mkdir -p $APP_DIR
chown cronbox:cronbox $APP_DIR

log "Setting up firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw allow 22/tcp    # SSH
    ufw allow 25/tcp    # SMTP (Postal)
    ufw allow 465/tcp   # SMTPS
    ufw allow 587/tcp   # Submission
    ufw --force enable
fi

log "Setup complete!"
echo ""
echo "========================================"
echo "Next steps:"
echo "========================================"
echo ""
echo "1. Clone the repository:"
echo "   sudo -u cronbox git clone <your-gitlab-repo> $APP_DIR"
echo ""
echo "2. Create .env file:"
echo "   cd $APP_DIR"
echo "   cp .env.example .env"
echo "   nano .env  # Fill in all values"
echo ""
echo "3. Generate Traefik dashboard password:"
echo "   apt-get install -y apache2-utils"
echo "   htpasswd -nB admin"
echo "   # Copy the hash to TRAEFIK_DASHBOARD_PASSWORD_HASH in .env"
echo ""
echo "4. Start the application:"
echo "   docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "========================================"
echo "GitLab CI/CD Setup:"
echo "========================================"
echo ""
echo "Add these variables in GitLab > Settings > CI/CD > Variables:"
echo ""
echo "  SSH_PRIVATE_KEY (type: File)"
echo "    - Generate: ssh-keygen -t ed25519 -C 'gitlab-deploy'"
echo "    - Add public key to /opt/cronbox/.ssh/authorized_keys"
echo ""
echo "  SSH_KNOWN_HOSTS (type: Variable)"
echo "    - Generate: ssh-keyscan <server-ip>"
echo ""
echo "  SSH_USER (type: Variable)"
echo "    - Value: cronbox"
echo ""
echo "  SSH_HOST (type: Variable)"
echo "    - Value: <your-server-ip-or-domain>"
echo ""
echo "  AUTO_DEPLOY (type: Variable, optional)"
echo "    - Value: true (to enable auto-deploy on push)"
echo ""
