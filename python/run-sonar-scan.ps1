#!/usr/bin/env pwsh
# Local SonarQube scan script for testing vulnerability detection

Write-Host "=== Local SonarQube Vulnerability Scan ===" -ForegroundColor Yellow
Write-Host "This script will run SonarQube scanner locally to test vulnerability detection" -ForegroundColor Yellow
Write-Host ""

# Check if sonar-scanner is available
$sonarScanner = Get-Command sonar-scanner -ErrorAction SilentlyContinue
if (-not $sonarScanner) {
    Write-Host "SonarQube Scanner not found. Please install it first:" -ForegroundColor Red
    Write-Host "1. Download from: https://docs.sonarqube.org/latest/analysis/scan/sonarscanner/" -ForegroundColor White
    Write-Host "2. Add to PATH" -ForegroundColor White
    Write-Host "3. Configure SONAR_HOST_URL and SONAR_TOKEN" -ForegroundColor White
    exit 1
}

# Set location
Set-Location -Path "c:\Dev\scai\python"

# Check for required environment variables
if (-not $env:SONAR_HOST_URL) {
    Write-Host "Warning: SONAR_HOST_URL not set. Using default localhost:9000" -ForegroundColor Yellow
    $env:SONAR_HOST_URL = "http://localhost:9000"
}

if (-not $env:SONAR_TOKEN) {
    Write-Host "Error: SONAR_TOKEN environment variable is required" -ForegroundColor Red
    Write-Host "Set it with: `$env:SONAR_TOKEN = 'your-token'" -ForegroundColor White
    exit 1
}

Write-Host "SonarQube Configuration:" -ForegroundColor Cyan
Write-Host "Host: $env:SONAR_HOST_URL" -ForegroundColor White
Write-Host "Project: swft-python" -ForegroundColor White
Write-Host ""

# Run coverage first if pytest is available
Write-Host "Running tests with coverage..." -ForegroundColor Cyan
try {
    python -m pytest tests/ -v --cov=app --cov-report=xml:coverage.xml --cov-report=term
    Write-Host "Coverage report generated" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not generate coverage report" -ForegroundColor Yellow
}

# Run SonarQube scanner
Write-Host "`nRunning SonarQube scanner..." -ForegroundColor Cyan
Write-Host "Expected to find multiple security vulnerabilities:" -ForegroundColor Yellow
Write-Host "- Hardcoded secrets" -ForegroundColor Red
Write-Host "- Command injection" -ForegroundColor Red  
Write-Host "- SQL injection" -ForegroundColor Red
Write-Host "- Insecure deserialization" -ForegroundColor Red
Write-Host "- Weak cryptography" -ForegroundColor Red
Write-Host ""

# Run the scanner
sonar-scanner `
  -Dsonar.projectKey=swft-python `
  -Dsonar.sources=app,vulnerable_module.py,vulnerable_deploy.py `
  -Dsonar.host.url=$env:SONAR_HOST_URL `
  -Dsonar.login=$env:SONAR_TOKEN `
  -Dsonar.python.coverage.reportPaths=coverage.xml `
  -Dsonar.qualitygate.wait=false `
  -Dsonar.verbose=true

$scanResult = $LASTEXITCODE

Write-Host "`n=== Scan Complete ===" -ForegroundColor Green
if ($scanResult -eq 0) {
    Write-Host "✅ SonarQube scan completed successfully" -ForegroundColor Green
    Write-Host "View results at: $env:SONAR_HOST_URL/dashboard?id=swft-python" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Expected findings:" -ForegroundColor Yellow
    Write-Host "• Security Hotspots: Multiple high-severity issues" -ForegroundColor White
    Write-Host "• Code Smells: Maintainability issues" -ForegroundColor White  
    Write-Host "• Bugs: Potential runtime issues" -ForegroundColor White
} else {
    Write-Host "⚠️ SonarQube scan completed with issues (expected for this test project)" -ForegroundColor Yellow
    Write-Host "Check the SonarQube dashboard for detailed vulnerability reports" -ForegroundColor White
}

Write-Host "`nNext steps:" -ForegroundColor Green
Write-Host "1. Open SonarQube dashboard" -ForegroundColor White
Write-Host "2. Review Security Hotspots tab" -ForegroundColor White
Write-Host "3. Check Issues tab for detailed findings" -ForegroundColor White
Write-Host "4. Review Code Quality metrics" -ForegroundColor White