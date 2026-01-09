# Frontend Dockerfile - Multi-stage build
# Security-hardened for production use

# Build stage
FROM node:20-alpine AS builder

# Security: Add labels
LABEL maintainer="CronBox Team"
LABEL stage="builder"

WORKDIR /app

# Copy package files first (for better layer caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --ignore-scripts

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Security: Add labels
LABEL maintainer="CronBox Team"
LABEL version="1.0"
LABEL description="CronBox Frontend"

# Security: Remove default nginx user and create custom one
RUN addgroup -g 1000 -S cronbox && \
    adduser -u 1000 -S cronbox -G cronbox

# Security: Remove unnecessary packages and files
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets with proper ownership
COPY --from=builder --chown=cronbox:cronbox /app/dist /usr/share/nginx/html

# Copy nginx config
COPY --chown=cronbox:cronbox nginx.conf /etc/nginx/conf.d/default.conf

# Security: Set proper permissions
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R cronbox:cronbox /var/cache/nginx && \
    chown -R cronbox:cronbox /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown cronbox:cronbox /var/run/nginx.pid

# Security: Switch to non-root user
USER cronbox

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
