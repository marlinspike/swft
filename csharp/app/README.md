# C# Hello World (.NET 8 on Alpine)

Minimal .NET 8 console app demonstrating a hardened multi-stage Docker build (SDK → runtime, non-root, caching) inside `csharp/app/src/HelloWorld`.

## Folder layout

```text
csharp/
	Dockerfile                      # Multi-stage build (restore, build, publish, runtime)
	app/src/HelloWorld/             # Project source (.csproj + Program.cs)
	scripts/compare-image-sizes.ps1 # Utility to compare build vs runtime image sizes
```

## Build & run locally (PowerShell)

```powershell
cd csharp
docker build -t csharp-hello:dev .
docker run --rm csharp-hello:dev
```

## Dockerfile stages (summary)

| Stage   | Purpose                                   | Notes |
|---------|-------------------------------------------|-------|
| restore | Restore NuGet packages using csproj only  | BuildKit cache mount speeds repeated restores |
| build   | Compile project (Release)                 | Output in /app/build (not shipped) |
| publish | Publish deployable assemblies             | Output copied to final image |
| runtime | Final minimal runtime-only image          | Non-root user, hardened env vars |

### Why separate build and runtime? (simple)

We build the app in an SDK image (has compilers) and then copy only the published output into a small runtime image (no compilers). This keeps the final image smaller, faster to pull, and reduces security risk because unnecessary tools are left behind.

## Common image tagging

```powershell
$sha = (git rev-parse --short HEAD)
docker build -t csharp-hello:$sha -t csharp-hello:latest .
```

## Security / hardening highlights

- Official Microsoft .NET 8 Alpine images.
- Non-root `app` user in final stage.
- Diagnostics disabled, globalization invariant reduces size.
- SDK excluded from runtime image via multi-stage build.

## compare-image-sizes.ps1 script

Path: `csharp/scripts/compare-image-sizes.ps1`

Purpose: Build the `build` and `runtime` stages separately, verify they differ, run the app, and report exact byte sizes.

### Parameters

| Name | Default | Description |
|------|---------|-------------|
| `DockerfilePath` | `c-sharp/Dockerfile` | Legacy default; override to `csharp/Dockerfile`. |
| `Context`        | `c-sharp`            | Legacy default; override to `csharp`. |
| `ImageName`      | `csharp-hello`       | Base image name for tags. |
| `Tag`            | `sizecheck`          | Suffix tag to distinguish comparison images. |

### Usage examples

```powershell
# Basic (from repo root)
pwsh ./csharp/scripts/compare-image-sizes.ps1 -DockerfilePath csharp/Dockerfile -Context csharp

# Custom tag
pwsh ./csharp/scripts/compare-image-sizes.ps1 -DockerfilePath csharp/Dockerfile -Context csharp -Tag perf

# Different image base name
pwsh ./csharp/scripts/compare-image-sizes.ps1 -DockerfilePath csharp/Dockerfile -Context csharp -ImageName csharp-demo -Tag test1
```

### Sample output

```text
Building build stage image...
Building runtime stage image...
OK: Different image IDs
OK: SDKs present in build; none in runtime
OK: Runtime container executed (output trimmed):
Hello World
Build stage size:   238.12 MB (238123456 B)
Runtime stage size:  82.45 MB (82451234 B)
Difference:         155.67 MB
```

### Troubleshooting

- Ensure Docker Desktop is running (`docker info`).
- If sizes match, confirm Dockerfile uses distinct `BASE_SDK` and `BASE_RUNTIME` images.
- Permission errors: normally no admin rights needed.

