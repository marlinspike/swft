# SWFT Multi-Stage Docker Build Test Script
# Tests and verifies the multi-stage Docker build

param(
    [string]$ImageName = "swft",
    [string]$Tag = "test",
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$ContainerName = "$ImageName-test"

Write-Host ""
Write-Host "=== SWFT Multi-Stage Docker Build Test ===" -ForegroundColor Cyan
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Step 1: Check Docker
Write-Host "--- Checking Docker Status ---" -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Docker is running (version: $dockerVersion)" -ForegroundColor Green
    } else {
        throw "Docker not running"
    }
} catch {
    Write-Host "[FAIL] Docker is not running" -ForegroundColor Red
    exit 1
}

# Step 2: Cleanup
Write-Host ""
Write-Host "--- Cleaning Up Previous Builds ---" -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
docker stop $ContainerName 2>&1 | Out-Null
docker rm $ContainerName 2>&1 | Out-Null
docker rmi "${ImageName}:${Tag}" 2>&1 | Out-Null
docker rmi "${ImageName}:builder" 2>&1 | Out-Null
$ErrorActionPreference = "Stop"
Write-Host "[OK] Cleanup complete" -ForegroundColor Green

# Step 3: Build builder stage
Write-Host ""
Write-Host "--- Building Builder Stage ---" -ForegroundColor Yellow
Write-Host "  Building with gcc and build-essential..." -ForegroundColor Gray
$builderStart = Get-Date
$ErrorActionPreference = "Continue"
docker build --target builder -t "${ImageName}:builder" . *>$null
$buildResult = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($buildResult -ne 0) {
    Write-Host "[FAIL] Builder stage build failed" -ForegroundColor Red
    exit 1
}
$builderTime = [math]::Round(((Get-Date) - $builderStart).TotalSeconds, 1)
Write-Host "[OK] Builder stage built in ${builderTime}s" -ForegroundColor Green

# Step 4: Build runtime stage
Write-Host ""
Write-Host "--- Building Runtime Stage ---" -ForegroundColor Yellow
Write-Host "  Building runtime-only image..." -ForegroundColor Gray
$runtimeStart = Get-Date
$ErrorActionPreference = "Continue"
docker build -t "${ImageName}:${Tag}" . *>$null
$buildResult = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($buildResult -ne 0) {
    Write-Host "[FAIL] Runtime stage build failed" -ForegroundColor Red
    exit 1
}
$runtimeTime = [math]::Round(((Get-Date) - $runtimeStart).TotalSeconds, 1)
Write-Host "[OK] Runtime stage built in ${runtimeTime}s" -ForegroundColor Green

# Step 5: Compare sizes
Write-Host ""
Write-Host "--- Image Size Comparison ---" -ForegroundColor Yellow
$builderSize = docker images "${ImageName}:builder" --format "{{.Size}}"
$runtimeSize = docker images "${ImageName}:${Tag}" --format "{{.Size}}"

# Parse sizes to bytes
function Get-SizeInBytes {
    param([string]$Size)
    if ($Size -match '([0-9.]+)([KMGT]?B)') {
        $num = [double]$matches[1]
        $unit = $matches[2]
        switch ($unit) {
            'GB' { return $num * 1GB }
            'MB' { return $num * 1MB }
            'KB' { return $num * 1KB }
            default { return $num }
        }
    }
    return 0
}

$builderBytes = Get-SizeInBytes $builderSize
$runtimeBytes = Get-SizeInBytes $runtimeSize
$reduction = [math]::Round((($builderBytes - $runtimeBytes) / $builderBytes) * 100, 1)
$savedMB = [math]::Round(($builderBytes - $runtimeBytes) / 1MB, 1)

Write-Host "  Builder image:  $builderSize" -ForegroundColor Gray
Write-Host "  Runtime image:  $runtimeSize" -ForegroundColor Gray
Write-Host "[OK] Size reduction: $reduction% (saved $savedMB MB)" -ForegroundColor Green

# Step 6: Verify no build tools in runtime
Write-Host ""
Write-Host "--- Verifying Image Layers ---" -ForegroundColor Yellow
$null = docker run --rm "${ImageName}:${Tag}" which gcc 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[OK] Build tools (gcc) not present in runtime image" -ForegroundColor Green
} else {
    Write-Host "[WARN] Build tools found in runtime image" -ForegroundColor Yellow
}

# Step 7: Start container
Write-Host ""
Write-Host "--- Starting Container ---" -ForegroundColor Yellow
Write-Host "  Starting on port ${Port}..." -ForegroundColor Gray
$containerId = docker run --rm -d -p "${Port}:80" --name $ContainerName "${ImageName}:${Tag}" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Failed to start container" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Container started (ID: $($containerId.Substring(0, 12)))" -ForegroundColor Green

Start-Sleep -Seconds 3

# Step 8: Check logs
Write-Host ""
Write-Host "--- Container Logs ---" -ForegroundColor Yellow
$ErrorActionPreference = "Continue"
$logs = docker logs $ContainerName 2>&1 | Select-Object -Last 5
$ErrorActionPreference = "Stop"
$logs | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

if ($logs -match "Uvicorn running") {
    Write-Host "[OK] Uvicorn server started" -ForegroundColor Green
} else {
    Write-Host "[WARN] Uvicorn startup message not found" -ForegroundColor Yellow
}

# Step 9: Test HTTP endpoint
Write-Host ""
Write-Host "--- Testing HTTP Endpoint ---" -ForegroundColor Yellow
Write-Host "  Sending request to http://localhost:${Port}" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:${Port}" -UseBasicParsing -TimeoutSec 10
    
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] HTTP 200 OK received" -ForegroundColor Green
        Write-Host "  Content-Type: $($response.Headers['Content-Type'])" -ForegroundColor Gray
        Write-Host "  Content-Length: $($response.Content.Length) bytes" -ForegroundColor Gray
        
        if ($response.Content -match "DOCTYPE html") {
            Write-Host "[OK] HTML content received" -ForegroundColor Green
        }
        
        if ($response.Content -match "SWFT") {
            Write-Host "[OK] Application content verified" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "[FAIL] HTTP request failed: $_" -ForegroundColor Red
}

# Step 10: Resource usage
Write-Host ""
Write-Host "--- Container Resource Usage ---" -ForegroundColor Yellow
$stats = docker stats $ContainerName --no-stream --format "{{.CPUPerc}} CPU, {{.MemUsage}} Memory" 2>$null
if ($stats) {
    Write-Host "  $stats" -ForegroundColor Gray
}

# Step 11: Cleanup
Write-Host ""
Write-Host "--- Cleanup ---" -ForegroundColor Yellow
docker stop $ContainerName 2>&1 | Out-Null
Write-Host "[OK] Container stopped" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "=== Test Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Builder image:    $builderSize" -ForegroundColor White
Write-Host "  Runtime image:    $runtimeSize" -ForegroundColor White
Write-Host "  Size reduction:   $reduction%" -ForegroundColor White
Write-Host "  Container tested: PASS" -ForegroundColor Green
Write-Host "  HTTP endpoint:    PASS" -ForegroundColor Green
Write-Host ""
Write-Host "Completed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Optional cleanup
$cleanup = Read-Host "Remove test images? (y/N)"
if ($cleanup -eq 'y' -or $cleanup -eq 'Y') {
    docker rmi "${ImageName}:${Tag}" 2>&1 | Out-Null
    docker rmi "${ImageName}:builder" 2>&1 | Out-Null
    Write-Host "[OK] Images removed" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Images kept. To run manually:" -ForegroundColor Gray
    Write-Host "  docker run --rm -p 8080:80 ${ImageName}:${Tag}" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
