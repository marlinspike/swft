#!/usr/bin/env pwsh
# PowerShell script to run Trivy vulnerability scans on the vulnerable Python project

Write-Host "=== Trivy Vulnerability Scan for Test Project ===" -ForegroundColor Yellow
Write-Host "This script will scan for vulnerabilities intentionally added for testing" -ForegroundColor Yellow
Write-Host ""

# Change to the python directory
Set-Location -Path "c:\Dev\scai\python"

Write-Host "1. Scanning filesystem for vulnerabilities..." -ForegroundColor Cyan
trivy fs --format table --severity HIGH,CRITICAL .

Write-Host "`n2. Scanning requirements.txt for vulnerable dependencies..." -ForegroundColor Cyan
trivy fs --format table --severity HIGH,CRITICAL requirements.txt

Write-Host "`n3. Scanning for hardcoded secrets..." -ForegroundColor Cyan
trivy fs --scanners secret --format table .

Write-Host "`n4. Building Docker image..." -ForegroundColor Cyan
docker build -t vulnerable-python-app:test .

Write-Host "`n5. Scanning Docker image for vulnerabilities..." -ForegroundColor Cyan
trivy image --format table --severity HIGH,CRITICAL vulnerable-python-app:test

Write-Host "`n6. Generating detailed JSON report..." -ForegroundColor Cyan
trivy fs --format json --output vulnerability-report.json .

Write-Host "`n7. Generating SARIF report for CI/CD integration..." -ForegroundColor Cyan
trivy fs --format sarif --output vulnerability-report.sarif .

Write-Host "`n=== SCAN COMPLETE ===" -ForegroundColor Green
Write-Host "Expected vulnerabilities found in this test project:" -ForegroundColor Yellow
Write-Host "- CVE-2021-32677 (FastAPI)" -ForegroundColor Red
Write-Host "- CVE-2020-28493 (Jinja2)" -ForegroundColor Red
Write-Host "- CVE-2021-29510 (Pydantic)" -ForegroundColor Red
Write-Host "- CVE-2022-25896 (Requests)" -ForegroundColor Red
Write-Host "- CVE-2021-34552 (Pillow)" -ForegroundColor Red
Write-Host "- CVE-2021-42036 (PyYAML)" -ForegroundColor Red
Write-Host "- CVE-2021-37573 (Cryptography)" -ForegroundColor Red
Write-Host "- Multiple Django/Flask CVEs" -ForegroundColor Red
Write-Host "- Hardcoded secrets and credentials" -ForegroundColor Red
Write-Host "- Insecure Docker configurations" -ForegroundColor Red
Write-Host ""
Write-Host "Reports generated:" -ForegroundColor Green
Write-Host "- vulnerability-report.json (detailed JSON report)" -ForegroundColor White
Write-Host "- vulnerability-report.sarif (SARIF format for CI/CD)" -ForegroundColor White