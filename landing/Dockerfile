# Landing Dockerfile - Multi-stage build
# Security-hardened for production use

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage - using serve instead of nginx
FROM node:20-alpine

# Security: Add labels
LABEL maintainer="CronBox Team"
LABEL version="1.0"
LABEL description="CronBox Landing"

# Security: Create non-root user
RUN addgroup -g 1000 cronbox && \
    adduser -u 1000 -G cronbox -s /bin/sh -D cronbox

# Install serve globally
RUN npm install -g serve@14

WORKDIR /app

# Copy built files
COPY --from=builder --chown=cronbox:cronbox /app/dist /app

# Create health endpoint file
RUN echo "OK" > /app/health

# Security: Switch to non-root user
USER cronbox

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run serve with SPA mode (-s) on port 3000
CMD ["serve", "-s", "-l", "3000"]
