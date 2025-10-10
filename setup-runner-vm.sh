#!/bin/bash
#
# Azure VM Self-Hosted Runner Setup Script
# This script installs all dependencies needed for the SWFT CI/CD pipeline
#
# Usage: sudo bash setup-runner-vm.sh
#

set -euo pipefail

echo "=========================================="
echo "SWFT Pipeline - Azure VM Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "❌ Please run as root (use sudo)"
   exit 1
fi

echo "📦 Updating system packages..."
apt-get update -y
apt-get upgrade -y

# ============================================
# 1. GITHUB ACTIONS RUNNER
# ============================================
echo ""
echo "🏃 Installing GitHub Actions Runner..."

RUNNER_VERSION="2.321.0"  # Update to latest version
RUNNER_USER="runner"

# Create runner user if doesn't exist
if ! id "$RUNNER_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$RUNNER_USER"
    echo "✅ Created user: $RUNNER_USER"
fi

# Add runner to docker group (will be created later)
usermod -aG docker "$RUNNER_USER" || true

# Download and install runner
cd /home/$RUNNER_USER
if [ ! -d "actions-runner" ]; then
    mkdir -p actions-runner
    cd actions-runner
    
    curl -o actions-runner-linux-x64.tar.gz -L \
        "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
    
    tar xzf actions-runner-linux-x64.tar.gz
    rm actions-runner-linux-x64.tar.gz
    
    chown -R $RUNNER_USER:$RUNNER_USER /home/$RUNNER_USER/actions-runner
    echo "✅ GitHub Actions Runner installed"
else
    echo "✅ GitHub Actions Runner already installed"
fi

# ============================================
# 2. DOCKER & DOCKER BUILDX
# ============================================
echo ""
echo "🐳 Installing Docker..."

if ! command -v docker &> /dev/null; then
    # Install Docker
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # Add Docker's official GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start Docker
    systemctl start docker
    systemctl enable docker

    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Verify Docker Buildx
docker buildx version || echo "⚠️  Docker Buildx not available"

# ============================================
# 3. AZURE CLI
# ============================================
echo ""
echo "☁️  Installing Azure CLI..."

if ! command -v az &> /dev/null; then
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash
    echo "✅ Azure CLI installed"
else
    echo "✅ Azure CLI already installed"
fi

az version

# ============================================
# 4. PYTHON 3.11
# ============================================
echo ""
echo "🐍 Installing Python 3.11..."

apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip

# Set Python 3.11 as default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

python3 --version
echo "✅ Python 3.11 installed"

# Install pip for Python 3.11
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Install pytest and coverage tools
pip3 install pytest pytest-cov

# ============================================
# 5. JAVA 17 (for SonarQube)
# ============================================
echo ""
echo "☕ Installing Java 17..."

apt-get install -y openjdk-17-jdk
java -version
echo "✅ Java 17 installed"

# ============================================
# 6. JQ (JSON processor)
# ============================================
echo ""
echo "📝 Installing jq..."

apt-get install -y jq
jq --version
echo "✅ jq installed"

# ============================================
# 7. GIT
# ============================================
echo ""
echo "📚 Installing Git..."

apt-get install -y git
git --version
echo "✅ Git installed"

# ============================================
# 8. COSIGN (for image signing)
# ============================================
echo ""
echo "🔐 Installing Cosign..."

COSIGN_VERSION="v2.2.3"
curl -Lo /usr/local/bin/cosign \
    "https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64"
chmod +x /usr/local/bin/cosign
cosign version
echo "✅ Cosign installed"

# ============================================
# 9. ADDITIONAL TOOLS
# ============================================
echo ""
echo "🔧 Installing additional tools..."

apt-get install -y \
    curl \
    wget \
    unzip \
    tar \
    gzip \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https \
    build-essential

echo "✅ Additional tools installed"

# ============================================
# 10. CLEANUP
# ============================================
echo ""
echo "🧹 Cleaning up..."

apt-get autoremove -y
apt-get clean

# ============================================
# SUMMARY
# ============================================
echo ""
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Installed versions:"
echo "  - Docker:        $(docker --version)"
echo "  - Docker Buildx: $(docker buildx version)"
echo "  - Azure CLI:     $(az --version | head -n1)"
echo "  - Python:        $(python3 --version)"
echo "  - Java:          $(java -version 2>&1 | head -n1)"
echo "  - Git:           $(git --version)"
echo "  - jq:            $(jq --version)"
echo "  - Cosign:        $(cosign version 2>&1 | head -n1)"
echo ""
echo "=========================================="
echo "📋 NEXT STEPS:"
echo "=========================================="
echo ""
echo "1. Configure GitHub Actions Runner:"
echo "   sudo su - runner"
echo "   cd actions-runner"
echo "   ./config.sh --url https://github.com/YOUR-ORG/YOUR-REPO --token YOUR-TOKEN"
echo ""
echo "2. Start the runner as a service:"
echo "   sudo ./svc.sh install"
echo "   sudo ./svc.sh start"
echo ""
echo "3. Configure Azure CLI (if not using managed identity):"
echo "   az login"
echo ""
echo "4. Add GitHub Secrets to your repository:"
echo "   - AZURE_CLIENT_ID"
echo "   - AZURE_CLIENT_SECRET"
echo "   - AZURE_TENANT_ID"
echo "   - AZURE_SUBSCRIPTION_ID"
echo "   - ACR_LOGIN_SERVER"
echo "   - ACR_USERNAME"
echo "   - ACR_PASSWORD"
echo "   - AZURE_STORAGE_ACCOUNT"
echo "   - COSIGN_KEY_B64"
echo "   - COSIGN_PUB_KEY_B64"
echo "   - SONAR_TOKEN"
echo "   - SONAR_HOST_URL"
echo "   - IMAGE_TAG"
echo ""
echo "5. Test the runner:"
echo "   Push to main branch or trigger workflow manually"
echo ""
echo "=========================================="
