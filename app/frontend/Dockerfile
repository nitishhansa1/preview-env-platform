# ==============================================================================
# React Frontend Dockerfile (Multi-stage build, Non-root nginx-unprivileged)
# ==============================================================================
# Purpose:
#   Builds the React/Vite single-page application into optimized static assets
#   and serves them using the hardened, non-root nginxinc/nginx-unprivileged image.
#
# Highlights:
#   - node:20-alpine compiles JSX and assets.
#   - nginxinc/nginx-unprivileged:alpine runs as unprivileged user (UID 101) on port 8080.
#   - Exposes port 8080 (standard for unprivileged non-root NGINX).
#   - Native HEALTHCHECK testing /healthz.
# ==============================================================================

# --- Stage 1: Build React static assets ---
FROM node:26-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for Docker layer caching
COPY package*.json ./

# Clean installation of dependencies
RUN npm ci --prefer-offline --no-audit

# Copy source code and build production bundle
COPY . .
RUN npm run build


# --- Stage 2: Minimal Non-Root Web Server ---
FROM nginxinc/nginx-unprivileged:alpine AS runner

# Remove default unprivileged configuration
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy custom NGINX server configuration
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/preview-app.conf

# Copy compiled static HTML/JS/CSS assets from builder stage
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

USER nginx

EXPOSE 8080

# Native healthcheck querying the /healthz endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
