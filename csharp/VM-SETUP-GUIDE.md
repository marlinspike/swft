# Azure VM Self-Hosted Runner Setup Guide

## Overview

This guide covers setting up an Azure VM to run your SWFT CI/CD pipeline as a self-hosted GitHub Actions runner.

---

## Prerequisites

- Azure VM running **Ubuntu 20.04 or 22.04**
- VM Size: **Standard_D4s_v3** or larger (4 vCPU, 16 GB RAM minimum)
- **80 GB disk space** minimum
- SSH access to the VM
- GitHub repository admin access

---

## Quick Setup

### 1. SSH into Your Azure VM

```bash
ssh azureuser@<your-vm-ip>
```

### 2. Run the Setup Script

```bash
# Copy the setup script to the VM
scp setup-runner-vm.sh azureuser@<your-vm-ip>:~/

# SSH into VM and run
ssh azureuser@<your-vm-ip>
sudo bash setup-runner-vm.sh
```

The script installs:
- ✅ GitHub Actions Runner
- ✅ Docker + Docker Buildx
- ✅ Azure CLI
- ✅ Python 3.11
- ✅ Java 17 (for SonarQube)
- ✅ jq (JSON processor)
- ✅ Git
- ✅ Cosign (image signing)
- ✅ Additional build tools

---

## Manual Installation (If Script Fails)

### 1. Install Docker

```bash
# Update packages
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker buildx version
```

### 2. Install Azure CLI

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az --version
```

### 3. Install Python 3.11

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set as default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install pytest
pip3 install pytest pytest-cov
```

### 4. Install Java 17

```bash
sudo apt-get install -y openjdk-17-jdk
java -version
```

### 5. Install jq

```bash
sudo apt-get install -y jq
jq --version
```

### 6. Install Cosign

```bash
COSIGN_VERSION="v2.2.3"
curl -Lo /tmp/cosign https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}/cosign-linux-amd64
sudo mv /tmp/cosign /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign
cosign version
```

### 7. Install Git

```bash
sudo apt-get install -y git
git --version
```

---

## Configure GitHub Actions Runner

### 1. Get Runner Token

Go to your GitHub repository:
```
Settings → Actions → Runners → New self-hosted runner
```

Copy the token provided.

### 2. Install Runner

```bash
# Create runner user
sudo useradd -m -s /bin/bash runner
sudo usermod -aG docker runner

# Switch to runner user
sudo su - runner

# Download runner
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz

# Extract
tar xzf actions-runner-linux-x64.tar.gz
rm actions-runner-linux-x64.tar.gz

# Configure
./config.sh --url https://github.com/YOUR-ORG/YOUR-REPO --token YOUR-TOKEN

# When prompted:
# - Runner group: Default
# - Runner name: azure-vm-runner (or your choice)
# - Work folder: _work
# - Labels: self-hosted,Linux,X64
```

### 3. Install as Service

```bash
# Exit runner user
exit

# Install service as root
cd /home/runner/actions-runner
sudo ./svc.sh install runner
sudo ./svc.sh start

# Check status
sudo ./svc.sh status
```

### 4. Verify Runner

Go to your GitHub repository:
```
Settings → Actions → Runners
```

You should see your runner with a green "Idle" status.

---

## Configure GitHub Secrets

Add these secrets to your repository (Settings → Secrets → Actions):

### Azure Authentication
```
AZURE_CLIENT_ID          - Service Principal App ID
AZURE_CLIENT_SECRET      - Service Principal Secret
AZURE_TENANT_ID          - Azure AD Tenant ID
AZURE_SUBSCRIPTION_ID    - Azure Subscription ID
```

### Azure Container Registry
```
ACR_LOGIN_SERVER         - e.g., myacr.azurecr.io
ACR_USERNAME             - ACR username
ACR_PASSWORD             - ACR password
```

### Azure Storage
```
AZURE_STORAGE_ACCOUNT    - Storage account name
```

### Image Signing (Cosign)
```
COSIGN_KEY_B64           - Base64 encoded private key
COSIGN_PUB_KEY_B64       - Base64 encoded public key
```

### SonarQube
```
SONAR_TOKEN              - SonarQube authentication token
SONAR_HOST_URL           - SonarQube server URL
```

### Other
```
IMAGE_TAG                - Docker image tag (e.g., latest, v1.0.0)
```

---

## Generate Cosign Keys

If you don't have Cosign keys yet:

```bash
# On your local machine or VM
cosign generate-key-pair

# This creates:
# - cosign.key (private key)
# - cosign.pub (public key)

# Base64 encode for GitHub secrets
cat cosign.key | base64 -w 0 > cosign.key.b64
cat cosign.pub | base64 -w 0 > cosign.pub.b64

# Copy contents to GitHub secrets
cat cosign.key.b64  # → COSIGN_KEY_B64
cat cosign.pub.b64  # → COSIGN_PUB_KEY_B64
```

---

## Test the Pipeline

### 1. Trigger Manually

Go to GitHub:
```
Actions → SWFT Container CI/CD → Run workflow
```

### 2. Push to Main Branch

```bash
git add .
git commit -m "Test pipeline"
git push origin main
```

### 3. Monitor Logs

Watch the workflow execution in GitHub Actions tab.

---

## Troubleshooting

### Runner Not Connecting

```bash
# Check runner service
sudo systemctl status actions.runner.*

# View logs
sudo journalctl -u actions.runner.* -f

# Restart service
sudo ./svc.sh stop
sudo ./svc.sh start
```

### Docker Permission Denied

```bash
# Add runner user to docker group
sudo usermod -aG docker runner

# Restart runner service
sudo ./svc.sh stop
sudo ./svc.sh start
```

### Azure CLI Not Authenticated

```bash
# Login manually (for testing)
az login

# Or use service principal
az login --service-principal \
  -u $AZURE_CLIENT_ID \
  -p $AZURE_CLIENT_SECRET \
  --tenant $AZURE_TENANT_ID
```

### Python Version Issues

```bash
# Check Python version
python3 --version

# Should be 3.11.x
# If not, reinstall:
sudo apt-get install -y python3.11
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### Docker Buildx Not Available

```bash
# Install buildx plugin
docker buildx install

# Verify
docker buildx version
```

### Cosign Not Found

```bash
# Check installation
which cosign
cosign version

# Reinstall if needed
curl -Lo /tmp/cosign https://github.com/sigstore/cosign/releases/download/v2.2.3/cosign-linux-amd64
sudo mv /tmp/cosign /usr/local/bin/cosign
sudo chmod +x /usr/local/bin/cosign
```

---

## VM Sizing Recommendations

### Minimum (Development)
- **Size**: Standard_D2s_v3
- **vCPUs**: 2
- **RAM**: 8 GB
- **Disk**: 80 GB
- **Cost**: ~$70/month

### Recommended (Production)
- **Size**: Standard_D4s_v3
- **vCPUs**: 4
- **RAM**: 16 GB
- **Disk**: 128 GB
- **Cost**: ~$140/month

### High Performance
- **Size**: Standard_D8s_v3
- **vCPUs**: 8
- **RAM**: 32 GB
- **Disk**: 256 GB
- **Cost**: ~$280/month

---

## Security Considerations

### 1. Network Security

```bash
# Allow only necessary ports
# - SSH (22) from your IP
# - Outbound HTTPS (443)
# - No inbound HTTP/HTTPS needed
```

### 2. VM Updates

```bash
# Enable automatic security updates
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. Firewall

```bash
# Enable UFW
sudo ufw allow 22/tcp
sudo ufw enable
```

### 4. Monitoring

```bash
# Install Azure Monitor agent
# Go to Azure Portal → VM → Monitoring → Insights → Enable
```

---

## Maintenance

### Update Runner

```bash
sudo su - runner
cd actions-runner
./svc.sh stop
./config.sh remove
# Download new version and reconfigure
./svc.sh install
./svc.sh start
```

### Update Docker

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo systemctl restart docker
```

### Update Azure CLI

```bash
sudo apt-get update
sudo apt-get install -y azure-cli
```

---

## Cost Optimization

### 1. Auto-Shutdown

Configure VM to shut down during off-hours:
```
Azure Portal → VM → Auto-shutdown → Configure schedule
```

### 2. Use Spot Instances

For non-critical workloads, use Azure Spot VMs (up to 90% savings).

### 3. Deallocate When Not in Use

```bash
# Stop and deallocate
az vm deallocate --resource-group <rg> --name <vm-name>

# Start when needed
az vm start --resource-group <rg> --name <vm-name>
```

---

## Support

### Logs Location

- **Runner logs**: `/home/runner/actions-runner/_diag/`
- **Docker logs**: `sudo journalctl -u docker`
- **System logs**: `/var/log/syslog`

### Useful Commands

```bash
# Check runner status
sudo systemctl status actions.runner.*

# View runner logs
sudo journalctl -u actions.runner.* -f

# Check disk space
df -h

# Check memory
free -h

# Check Docker containers
docker ps -a

# Check Docker images
docker images
```

---

**Last Updated**: 2025-10-10  
**Pipeline Version**: 1.0  
**Runner Version**: 2.321.0
