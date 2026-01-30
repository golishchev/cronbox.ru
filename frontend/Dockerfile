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

# Install dependencies with cache mount (survives image prune)
RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts

# Copy source code
COPY . .

# Accept build args
ARG VITE_API_URL
ARG VITE_SENTRY_DSN
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_SENTRY_DSN=${VITE_SENTRY_DSN}

# Build the application
RUN npm run build

# Production stage - using serve instead of nginx
FROM node:20-alpine

# Security: Add labels
LABEL maintainer="CronBox Team"
LABEL version="1.0"
LABEL description="CronBox Frontend"

# Install serve globally
RUN npm install -g serve@14

WORKDIR /app

# Copy built assets (node user already exists with uid 1000)
COPY --from=builder --chown=node:node /app/dist /app

# Create health endpoint file
RUN echo "OK" > /app/health && chown node:node /app/health

# Security: Switch to non-root user
USER node

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run serve with SPA mode (-s) on port 3000
CMD ["serve", "-s", "-l", "3000"]
