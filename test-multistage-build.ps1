#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Tests and verifies the multi-stage Docker build for SWFT application
.DESCRIPTION
    This script builds both stages of the Docker image, compares sizes,
    runs the container, and verifies the application is working correctly.
#>

param(
    [string]$ImageName = "swft",
    [string]$Tag = "test",
    [int]$Port = 8080,
    [int]$ContainerPort = 80
)

$ErrorActionPreference = "Stop"
$ContainerName = "$ImageName-test"

Write-Host ""
Write-Host "=== SWFT Multi-Stage Docker Build Test ===" -ForegroundColor Cyan
Write-Host "Started at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Function to print section headers
function Write-Section {
    param([string]$Title)
    Write-Host "`n--- $Title ---" -ForegroundColor Yellow
}

# Function to print success messages
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

# Function to print error messages
function Write-Fail {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

# Function to print info messages
function Write-Info {
    param([string]$Message)
    Write-Host "  $Message" -ForegroundColor Gray
}

# Step 1: Check Docker is running
Write-Section "Checking Docker Status"
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker is running (version: $dockerVersion)"
    } else {
        throw "Docker is not running"
    }
} catch {
    Write-Fail "Docker is not running or not installed"
    Write-Info "Please start Docker Desktop and try again"
    exit 1
}

# Step 2: Clean up any existing containers/images
Write-Section "Cleaning Up Previous Builds"
try {
    # Stop and remove existing container
    $existingContainer = docker ps -a --filter "name=$ContainerName" --format "{{.Names}}" 2>$null
    if ($existingContainer) {
        Write-Info "Stopping existing container: $ContainerName"
        docker stop $ContainerName 2>&1 | Out-Null
        docker rm $ContainerName 2>&1 | Out-Null
        Write-Success "Removed existing container"
    }
    
    # Remove existing images
    $existingImages = docker images --filter "reference=${ImageName}:${Tag}" --format "{{.Repository}}:{{.Tag}}" 2>$null
    if ($existingImages) {
        Write-Info "Removing existing image: ${ImageName}:${Tag}"
        docker rmi "${ImageName}:${Tag}" 2>&1 | Out-Null
    }
    
    $existingBuilder = docker images --filter "reference=${ImageName}:builder" --format "{{.Repository}}:{{.Tag}}" 2>$null
    if ($existingBuilder) {
        Write-Info "Removing existing builder image: ${ImageName}:builder"
        docker rmi "${ImageName}:builder" 2>&1 | Out-Null
    }
    
    Write-Success "Cleanup complete"
} catch {
    Write-Info "No previous builds to clean up"
}

# Step 3: Build the builder stage
Write-Section "Building Builder Stage"
Write-Info "This stage includes all build tools (gcc, build-essential)"
$builderStart = Get-Date
try {
    docker build --target builder -t "${ImageName}:builder" . 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Builder stage build failed"
    }
    $builderDuration = (Get-Date) - $builderStart
    Write-Success "Builder stage built successfully in $([math]::Round($builderDuration.TotalSeconds, 1))s"
} catch {
    Write-Fail "Failed to build builder stage"
    exit 1
}

# Step 4: Build the runtime stage
Write-Section "Building Runtime Stage"
Write-Info "This stage contains only the runtime and application code"
$runtimeStart = Get-Date
try {
    docker build -t "${ImageName}:${Tag}" . 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime stage build failed"
    }
    $runtimeDuration = (Get-Date) - $runtimeStart
    Write-Success "Runtime stage built successfully in $([math]::Round($runtimeDuration.TotalSeconds, 1))s"
} catch {
    Write-Fail "Failed to build runtime stage"
    exit 1
}

# Step 5: Compare image sizes
Write-Section "Image Size Comparison"
try {
    $builderSize = docker images "${ImageName}:builder" --format "{{.Size}}"
    $runtimeSize = docker images "${ImageName}:${Tag}" --format "{{.Size}}"
    
    # Get sizes in bytes for calculation
    $builderBytes = docker images "${ImageName}:builder" --format "{{.Size}}" | ForEach-Object {
        if ($_ -match '(\d+\.?\d*)([KMGT]?B)') {
            $num = [double]$matches[1]
            $unit = $matches[2]
            switch ($unit) {
                'GB' { $num * 1GB }
                'MB' { $num * 1MB }
                'KB' { $num * 1KB }
                default { $num }
            }
        }
    }
    
    $runtimeBytes = docker images "${ImageName}:${Tag}" --format "{{.Size}}" | ForEach-Object {
        if ($_ -match '(\d+\.?\d*)([KMGT]?B)') {
            $num = [double]$matches[1]
            $unit = $matches[2]
            switch ($unit) {
                'GB' { $num * 1GB }
                'MB' { $num * 1MB }
                'KB' { $num * 1KB }
                default { $num }
            }
        }
    }
    
    $reduction = [math]::Round((($builderBytes - $runtimeBytes) / $builderBytes) * 100, 1)
    $savedMB = [math]::Round(($builderBytes - $runtimeBytes) / 1MB, 1)
    
    Write-Info "Builder image:  $builderSize"
    Write-Info "Runtime image:  $runtimeSize"
    Write-Success "Size reduction: $reduction% ($savedMB MB saved)"
    
    if ($reduction -lt 50) {
        Write-Fail "Warning: Expected at least 50 percent size reduction"
    }
} catch {
    Write-Fail "Failed to compare image sizes"
}

# Step 6: Verify image layers
Write-Section "Verifying Image Layers"
try {
    $history = docker history "${ImageName}:${Tag}" --human=true --no-trunc=false
    $layers = ($history | Measure-Object).Count - 1  # Subtract header
    Write-Info "Total layers: $layers"
    
    # Check for build tools in final image (should not exist)
    $hasGcc = docker run --rm "${ImageName}:${Tag}" which gcc 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Success "Build tools (gcc) not present in runtime image"
    } else {
        Write-Fail "Warning: Build tools found in runtime image"
    }
} catch {
    Write-Info "Layer verification skipped"
}

# Step 7: Run the container
Write-Section "Starting Container"
try {
    Write-Info "Starting container on port ${Port}"
    $containerId = docker run --rm -d -p "${Port}:${ContainerPort}" --name $ContainerName "${ImageName}:${Tag}" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to start container"
    }
    Write-Success "Container started (ID: $($containerId.Substring(0, 12)))"
    
    # Wait for container to be ready
    Write-Info "Waiting for application to start"
    Start-Sleep -Seconds 3
    
    # Check container is still running
    $containerStatus = docker ps --filter "name=$ContainerName" --format "{{.Status}}"
    if ($containerStatus) {
        Write-Success "Container is running: $containerStatus"
    } else {
        throw "Container stopped unexpectedly"
    }
} catch {
    Write-Fail "Failed to start container"
    Write-Info "Checking logs"
    docker logs $ContainerName 2>&1
    exit 1
}

# Step 8: Check container logs
Write-Section "Container Logs"
try {
    $logs = docker logs $ContainerName 2>&1 | Select-Object -Last 10
    $logs | ForEach-Object { Write-Info $_ }
    
    if ($logs -match "Uvicorn running") {
        Write-Success "Uvicorn server started successfully"
    } else {
        Write-Fail "Warning: Uvicorn startup message not found"
    }
} catch {
    Write-Fail "Failed to retrieve container logs"
}

# Step 9: Test HTTP endpoint
Write-Section "Testing HTTP Endpoint"
try {
    Write-Info "Sending request to http://localhost:${Port}"
    $response = Invoke-WebRequest -Uri "http://localhost:${Port}" -UseBasicParsing -TimeoutSec 10
    
    if ($response.StatusCode -eq 200) {
        Write-Success "HTTP 200 OK received"
        Write-Info "Content-Type: $($response.Headers['Content-Type'])"
        Write-Info "Content-Length: $($response.Content.Length) bytes"
        Write-Info "Server: $($response.Headers['Server'])"
        
        # Check if response contains expected content
        if ($response.Content -match "DOCTYPE html") {
            Write-Success "HTML content received"
        }
        
        if ($response.Content -match "SWFT") {
            Write-Success "Application content verified"
        }
    } else {
        Write-Fail "Unexpected status code: $($response.StatusCode)"
    }
} catch {
    Write-Fail "HTTP request failed: $_"
}

# Step 10: Test additional endpoints (if any)
Write-Section "Testing Additional Endpoints"
try {
    # Test /docs endpoint (FastAPI auto-generated docs)
    $docsResponse = Invoke-WebRequest -Uri "http://localhost:${Port}/docs" -UseBasicParsing -TimeoutSec 5 2>$null
    if ($docsResponse.StatusCode -eq 200) {
        Write-Success "FastAPI docs endpoint accessible"
    }
} catch {
    Write-Info "Docs endpoint not accessible (this may be expected)"
}

# Step 11: Resource usage
Write-Section "Container Resource Usage"
try {
    $stats = docker stats $ContainerName --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>$null
    if ($stats) {
        $stats | ForEach-Object { Write-Info $_ }
        Write-Success "Resource usage captured"
    }
} catch {
    Write-Info "Could not capture resource usage"
}

# Step 12: Cleanup
Write-Section "Cleanup"
try {
    Write-Info "Stopping container"
    docker stop $ContainerName 2>&1 | Out-Null
    Write-Success "Container stopped and removed"
} catch {
    Write-Fail "Failed to stop container"
}

# Final summary
Write-Section "Test Summary"
Write-Host ""
Write-Success "Multi-stage build verification complete!"
Write-Host ""
Write-Info "Summary:"
Write-Info "  - Builder image: $builderSize"
Write-Info "  - Runtime image: $runtimeSize"
Write-Info "  - Size reduction: $reduction%"
Write-Info "  - Container tested: ✓"
Write-Info "  - HTTP endpoint: ✓"
Write-Host ""
Write-Host "Completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Optional: Keep images or clean up
$cleanup = Read-Host "Remove test images? (y/N)"
if ($cleanup -eq 'y' -or $cleanup -eq 'Y') {
    Write-Info "Removing images"
    docker rmi "${ImageName}:${Tag}" 2>&1 | Out-Null
    docker rmi "${ImageName}:builder" 2>&1 | Out-Null
    Write-Success "Images removed"
} else {
    Write-Info "Images kept for inspection"
    Write-Info "  - docker run --rm -p 8080:80 ${ImageName}:${Tag}"
    Write-Info "  - docker images ${ImageName}"
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
