#!/usr/bin/env pwsh
# PowerShell script to install vulnerable dependencies for CVE testing (simplified approach)

Write-Host "Installing vulnerable dependencies for CVE testing..." -ForegroundColor Yellow
Write-Host "Using simplified approach to avoid build issues" -ForegroundColor Yellow

# Change to python directory
Set-Location -Path "c:\Dev\scai\python"

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Try simplified requirements first
Write-Host "`nTrying simplified requirements..." -ForegroundColor Cyan
try {
    python -m pip install -r requirements-simple.txt --no-cache-dir
    Write-Host "SUCCESS: Simplified requirements installed!" -ForegroundColor Green
    
    # Try to add more vulnerable packages individually
    Write-Host "`nAdding additional vulnerable packages..." -ForegroundColor Cyan
    
    $additional_packages = @(
        "pyyaml==5.3.1",
        "cryptography==3.4.8"
    )
    
    foreach ($pkg in $additional_packages) {
        try {
            Write-Host "Installing $pkg..." -ForegroundColor Cyan
            python -m pip install $pkg
        } catch {
            Write-Host "Skipping $pkg (build issues)" -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Host "Falling back to individual package installation..." -ForegroundColor Yellow
    
    # Essential packages that should install easily
    $essential_packages = @(
        "python-dotenv>=1.0.0",
        "pytest>=8.3.4",
        "pytest-cov>=4.1.0",
        "httpx>=0.23.0",
        "jinja2==2.11.0",
        "flask==1.1.4",
        "werkzeug==1.0.1",
        "fastapi==0.68.0",
        "uvicorn==0.15.0",
        "pydantic==1.8.2",
        "requests==2.25.1",
        "urllib3==1.26.5",
        "click==7.1.2",
        "setuptools==65.5.0"
    )
    
    foreach ($pkg in $essential_packages) {
        try {
            Write-Host "Installing $pkg..." -ForegroundColor Cyan
            python -m pip install $pkg
        } catch {
            Write-Host "Failed to install $pkg" -ForegroundColor Red
        }
    }
}

# Show what we successfully installed
Write-Host "`n=== INSTALLATION SUMMARY ===" -ForegroundColor Green
Write-Host "Checking installed vulnerable packages:" -ForegroundColor Yellow

$vulnerable_packages = @("fastapi", "uvicorn", "jinja2", "pydantic", "requests", "flask", "django", "urllib3", "setuptools")

foreach ($pkg in $vulnerable_packages) {
    try {
        $version = python -c "import $pkg; print($pkg.__version__)" 2>$null
        if ($version) {
            Write-Host "✓ $pkg $version" -ForegroundColor Green
        }
    } catch {
        # Package not installed or no version attribute
    }
}

Write-Host "`nInstallation complete! You can now run Trivy scans:" -ForegroundColor Cyan
Write-Host "  trivy fs --severity HIGH,CRITICAL ." -ForegroundColor White
Write-Host "  docker build -t test-app . && trivy image test-app" -ForegroundColor White