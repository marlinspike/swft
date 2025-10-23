#!/usr/bin/env pwsh
# PowerShell script to install vulnerable dependencies for CVE testing

Write-Host "Installing vulnerable dependencies for CVE testing..." -ForegroundColor Yellow
Write-Host "This will install compatible vulnerable packages to avoid dependency conflicts" -ForegroundColor Yellow

# Change to python directory
Set-Location -Path "c:\Dev\scai\python"

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install compatible vulnerable dependencies from requirements.txt
Write-Host "`nInstalling from requirements.txt..." -ForegroundColor Cyan
try {
    python -m pip install -r requirements.txt --no-cache-dir
    Write-Host "SUCCESS: All dependencies installed!" -ForegroundColor Green
} catch {
    Write-Host "Installing packages individually to handle conflicts..." -ForegroundColor Yellow
    
    # Core dependencies first
    python -m pip install "python-dotenv>=1.0.0"
    python -m pip install "pytest>=8.3.4"
    python -m pip install "pytest-cov>=4.1.0"
    python -m pip install "httpx>=0.23.0"
    
    # Install Jinja2 first (required by Flask)
    python -m pip install "jinja2==2.11.0"
    
    # Install Flask that's compatible with Jinja2 2.x
    python -m pip install "flask==1.1.4"
    python -m pip install "werkzeug==1.0.1"
    
    # Install other vulnerable packages
    python -m pip install "fastapi==0.68.0"
    python -m pip install "uvicorn==0.15.0"
    python -m pip install "pydantic==1.8.2"
    python -m pip install "requests==2.25.1"
    python -m pip install "pillow==8.3.2"
    python -m pip install "pyyaml==5.3.1"
    python -m pip install "cryptography==3.4.8"
    python -m pip install "django==3.1.14"
    python -m pip install "click==7.1.2"
    python -m pip install "urllib3==1.26.5"
    python -m pip install "setuptools==65.5.0"
    python -m pip install "wheel==0.37.1"
}

Write-Host "`n=== INSTALLATION COMPLETE ===" -ForegroundColor Green
Write-Host "Vulnerable packages installed for CVE testing:" -ForegroundColor Yellow
Write-Host "- FastAPI 0.68.0 (CVE-2021-32677)" -ForegroundColor Red
Write-Host "- Jinja2 2.11.0 (CVE-2020-28493)" -ForegroundColor Red
Write-Host "- Flask 1.1.4 (CVE-2023-30861)" -ForegroundColor Red
Write-Host "- Pydantic 1.8.2 (CVE-2021-29510)" -ForegroundColor Red
Write-Host "- Requests 2.25.1 (CVE-2022-25896)" -ForegroundColor Red
Write-Host "- Django 3.1.14 (CVE-2021-35042)" -ForegroundColor Red
Write-Host "- And more..." -ForegroundColor Red

Write-Host "`nRun the following to test with Trivy:" -ForegroundColor Green
Write-Host "  .\run-trivy-scan.ps1" -ForegroundColor White
Write-Host "  or" -ForegroundColor White
Write-Host "  trivy fs --severity HIGH,CRITICAL ." -ForegroundColor White