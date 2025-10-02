param(
  [string]$DockerfilePath = "c-sharp/Dockerfile",
  [string]$Context = "c-sharp",
  [string]$ImageName = "csharp-hello",
  [string]$Tag = "sizecheck"
)

# Requires: Docker Desktop and PowerShell
$ErrorActionPreference = 'Stop'

function Invoke-Docker($args) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = 'docker'
  $psi.Arguments = $args
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $p = [System.Diagnostics.Process]::Start($psi)
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()
  if ($p.ExitCode -ne 0) {
    throw "docker $args failed: $stderr"
  }
  return $stdout
}

function Parse-SizeBytes([string]$sizeStr) {
  # Accepts values like '72.1MB', '1.23GB', '987kB', '123B'
  if ($sizeStr -match '^(?<num>[0-9.]+)\s*(?<unit>[KMG]?B)$') {
    $n = [double]$matches['num']
    switch ($matches['unit'].ToUpper()) {
      'B'  { return [int64]$n }
      'KB' { return [int64]($n * 1KB) }
      'MB' { return [int64]($n * 1MB) }
      'GB' { return [int64]($n * 1GB) }
      default { return [int64]$n }
    }
  }
  throw "Unrecognized size format: $sizeStr"
}

function Format-Size([long]$bytes) {
  if ($bytes -ge 1GB) { return '{0:N2} GB' -f ($bytes/1GB) }
  if ($bytes -ge 1MB) { return '{0:N2} MB' -f ($bytes/1MB) }
  if ($bytes -ge 1KB) { return '{0:N2} KB' -f ($bytes/1KB) }
  return "$bytes B"
}

$buildTag   = "local/${ImageName}:$Tag-build"
$runtimeTag = "local/${ImageName}:$Tag-runtime"

Write-Host "Building build stage image..." -ForegroundColor Cyan
& docker build --target build -f $DockerfilePath -t $buildTag $Context
if ($LASTEXITCODE -ne 0) { throw "docker build (build stage) failed with exit code $LASTEXITCODE" }

Write-Host "Building runtime stage image..." -ForegroundColor Cyan
& docker build --target runtime -f $DockerfilePath -t $runtimeTag $Context
if ($LASTEXITCODE -ne 0) { throw "docker build (runtime stage) failed with exit code $LASTEXITCODE" }

Write-Host "Verifying images are distinct and stage contents make sense..." -ForegroundColor Cyan
# Distinct image IDs
$buildId   = (& docker image inspect $buildTag --format '{{.Id}}').Trim()
if ($LASTEXITCODE -ne 0 -or -not $buildId) { throw "Failed to inspect image id for $buildTag" }
$runtimeId = (& docker image inspect $runtimeTag --format '{{.Id}}').Trim()
if ($LASTEXITCODE -ne 0 -or -not $runtimeId) { throw "Failed to inspect image id for $runtimeTag" }
if ($buildId -eq $runtimeId) { throw "Build and runtime images have the same ID. Expected them to differ." }
Write-Host "OK: Different image IDs" -ForegroundColor Green

# SDK present in build, absent in runtime
$buildSdks = (& docker run --rm --entrypoint sh $buildTag -lc 'dotnet --list-sdks 2>&1 || true') -join "`n"
$runtimeSdks = (& docker run --rm --entrypoint sh $runtimeTag -lc 'dotnet --list-sdks 2>&1 || true') -join "`n"
if (-not $buildSdks.Trim()) { throw "Expected SDKs in build image, but none detected." }
if ($runtimeSdks.Trim() -and ($runtimeSdks -notmatch 'No installed SDKs')) {
  throw "Expected no SDKs in runtime image, but got: $runtimeSdks"
}
Write-Host "OK: SDKs present in build; none in runtime" -ForegroundColor Green

# App executes in runtime image via default ENTRYPOINT
$appOutput = (& docker run --rm $runtimeTag) -join "`n"
if ($LASTEXITCODE -ne 0) { throw "Runtime image failed to run app (exit $LASTEXITCODE)" }
Write-Host "OK: Runtime container executed (output trimmed):" -ForegroundColor Green
Write-Host ($appOutput | Select-Object -First 1)

Write-Host "Inspecting image sizes..." -ForegroundColor Cyan
# Use fast, exact byte sizes from image inspect
$buildSizeRaw = (& docker image inspect $buildTag --format '{{.Size}}').Trim()
if ($LASTEXITCODE -ne 0 -or -not $buildSizeRaw) { throw "Failed to inspect size for $buildTag" }
$runtimeSizeRaw = (& docker image inspect $runtimeTag --format '{{.Size}}').Trim()
if ($LASTEXITCODE -ne 0 -or -not $runtimeSizeRaw) { throw "Failed to inspect size for $runtimeTag" }

$buildBytes   = [int64]$buildSizeRaw
$runtimeBytes = [int64]$runtimeSizeRaw
$diffBytes    = $buildBytes - $runtimeBytes

$buildNice   = Format-Size $buildBytes
$runtimeNice = Format-Size $runtimeBytes
$diffNice    = Format-Size $diffBytes

Write-Host "Build stage size:   $buildNice (${buildBytes} B)" -ForegroundColor Yellow
Write-Host "Runtime stage size: $runtimeNice (${runtimeBytes} B)" -ForegroundColor Yellow
Write-Host "Difference:         $diffNice" -ForegroundColor Green

Write-Host "Tip: You can pass -Tag mytag to create unique tags, and -Context/-DockerfilePath to point elsewhere." -ForegroundColor DarkGray
