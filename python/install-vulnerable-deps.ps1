#!/usr/bin/env pwsh
# PowerShell script to install vulnerable dependencies for CVE testing

Write-Host "Installing vulnerable dependencies for CVE testing..." -ForegroundColor Yellow
Write-Host "This may show warnings - this is expected for vulnerable packages" -ForegroundColor Yellow

# Change to python directory
Set-Location -Path "python"

# Upgrade pip first
python -m pip install --upgrade pip

# Install packages that work well first
Write-Host "`nInstalling basic dependencies..." -ForegroundColor Cyan
python -m pip install python-dotenv pytest pytest-cov httpx

# Install vulnerable versions with specific handling
Write-Host "`nInstalling vulnerable packages..." -ForegroundColor Cyan

# FastAPI and related
python -m pip install "fastapi==0.68.0"
python -m pip install "uvicorn==0.15.0"
python -m pip install "click==7.1.2"

# Jinja2
python -m pip install "jinja2==2.11.0"

# Pydantic (compatible with Python 3.11)
python -m pip install "pydantic==1.8.2"

# Requests
python -m pip install "requests==2.25.1"

# Pillow (using a version that builds on Python 3.11)
python -m pip install "pillow==8.3.2"

# PyYAML with build isolation disabled
Write-Host "`nInstalling PyYAML (may take a moment)..." -ForegroundColor Cyan
python -m pip install "pyyaml==6.0" --no-cache-dir

# Cryptography (using version compatible with Python 3.11)
python -m pip install "cryptography==3.4.8"

# Django and Flask (not used in app but will trigger CVE scans)
python -m pip install "django==3.2.15"
python -m pip install "flask==2.0.3"
python -m pip install "werkzeug==2.0.3"

# Additional vulnerable packages for more CVEs
Write-Host "`nInstalling additional vulnerable packages..." -ForegroundColor Cyan
python -m pip install "urllib3==1.26.5"  # CVE-2021-33503
python -m pip install "setuptools==65.5.0"  # CVE-2022-40897
python -m pip install "wheel==0.37.1"  # CVE-2022-40898

Write-Host "`n=== INSTALLATION COMPLETE ===" -ForegroundColor Green
Write-Host "Vulnerable packages installed for CVE testing:" -ForegroundColor Yellow
Write-Host "- FastAPI 0.68.0 (CVE-2021-32677)" -ForegroundColor Red
Write-Host "- Uvicorn 0.15.0 (Multiple CVEs)" -ForegroundColor Red
Write-Host "- Jinja2 2.11.0 (CVE-2020-28493)" -ForegroundColor Red
Write-Host "- Pydantic 1.8.2 (CVE-2021-29510)" -ForegroundColor Red
Write-Host "- Requests 2.25.1 (CVE-2022-25896)" -ForegroundColor Red
Write-Host "- Pillow 8.3.2 (CVE-2021-34552)" -ForegroundColor Red
Write-Host "- Cryptography 3.4.8 (CVE-2021-37573)" -ForegroundColor Red
Write-Host "- Django 3.2.15 (CVE-2022-34265)" -ForegroundColor Red
Write-Host "- Flask 2.0.3 (CVE-2023-30861)" -ForegroundColor Red
Write-Host "- And more..." -ForegroundColor Red

Write-Host "`nYou can now run Trivy scans to detect these vulnerabilities!" -ForegroundColor Green