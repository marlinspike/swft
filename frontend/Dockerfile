# syntax=docker/dockerfile:1.7
##
# Production-ready build for the SWFT frontend.
# - Builder stage installs dependencies with npm ci and compiles the Vite bundle.
# - Runtime stage serves static assets with the unprivileged nginx image (runs as UID 101).
# Customize VITE_API_BASE_URL at build time if the backend lives elsewhere:
#   docker build -t swft-frontend --build-arg VITE_API_BASE_URL=https://api.example.com -f frontend/Dockerfile frontend
##

FROM node:20-alpine AS deps
WORKDIR /app
ENV NODE_ENV=production \
    PLAYWRIGHT_BROWSERS_PATH=0
COPY package.json package-lock.json ./
RUN npm ci --include=dev

FROM deps AS build
COPY . .
# Allow callers to change the API base URL during docker build without editing source.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build && npm prune --omit=dev

FROM nginxinc/nginx-unprivileged:1.27-bookworm AS runtime
USER root
# Pull in security updates for libxml2/libexpat/perl to match the patched Debian 12.11 variants.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libxml2 \
        libexpat1 \
        perl-base \
    && rm -rf /var/lib/apt/lists/*
USER 101
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
ENTRYPOINT ["nginx", "-g", "daemon off;"]
