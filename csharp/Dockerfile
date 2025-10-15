# syntax=docker/dockerfile:1.7

# Options for BASE_SDK/BASE_RUNTIME 
ARG BASE_SDK=mcr.microsoft.com/dotnet/sdk:8.0-alpine
ARG BASE_RUNTIME=mcr.microsoft.com/dotnet/runtime:8.0-alpine

# Restore
FROM ${BASE_SDK} AS restore
WORKDIR /src
COPY ./app/src/HelloWorld/HelloWorld.csproj ./app/src/HelloWorld/
RUN --mount=type=cache,target=/root/.nuget/packages \
	dotnet restore ./app/src/HelloWorld/HelloWorld.csproj --nologo

# Build
FROM ${BASE_SDK} AS build
WORKDIR /src
COPY . .
RUN --mount=type=cache,target=/root/.nuget/packages \
	dotnet restore ./app/src/HelloWorld/HelloWorld.csproj --nologo \
	&& dotnet build ./app/src/HelloWorld/HelloWorld.csproj \
		-c Release \
		-o /app/build \
		--no-restore \
		--nologo \
		-p:ContinuousIntegrationBuild=true

# Publish
FROM ${BASE_SDK} AS publish
WORKDIR /src
COPY . .
RUN --mount=type=cache,target=/root/.nuget/packages \
	dotnet restore ./app/src/HelloWorld/HelloWorld.csproj --nologo \
	&& dotnet publish ./app/src/HelloWorld/HelloWorld.csproj \
		-c Release \
		-o /app/publish \
		--no-restore \
		--nologo \
		-p:ContinuousIntegrationBuild=true

# Strict runtime (no SDK)
FROM ${BASE_RUNTIME} AS runtime
WORKDIR /app

# Build metadata for labels
ARG VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

# Hardening
ENV DOTNET_EnableDiagnostics=0 \
	DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

# Non-root (idempotent)
RUN if ! grep -q '^app:' /etc/group; then addgroup -S app; fi \
	&& if ! id -u app >/dev/null 2>&1; then adduser -S -G app app; fi
COPY --chown=app:app --from=publish /app/publish/ ./
USER app

# OCI labels
LABEL org.opencontainers.image.title="csharp-hello" \
	  org.opencontainers.image.description="Hello World .NET 8 console app (Alpine)" \
	  org.opencontainers.image.source="https://github.com/ISD-AI-Hero/scai" \
	  org.opencontainers.image.url="https://github.com/ISD-AI-Hero/scai" \
	  org.opencontainers.image.version="${VERSION}" \
	  org.opencontainers.image.revision="${VCS_REF}" \
	  org.opencontainers.image.created="${BUILD_DATE}"

STOPSIGNAL SIGTERM
ENTRYPOINT ["dotnet", "HelloWorld.dll"]
