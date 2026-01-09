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

# Production stage
FROM nginx:alpine

# Create non-root user
RUN addgroup -g 1000 cronbox && \
    adduser -u 1000 -G cronbox -s /bin/sh -D cronbox

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Set ownership
RUN chown -R cronbox:cronbox /usr/share/nginx/html && \
    chown -R cronbox:cronbox /var/cache/nginx && \
    chown -R cronbox:cronbox /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown cronbox:cronbox /var/run/nginx.pid

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Run as non-root user
USER cronbox

CMD ["nginx", "-g", "daemon off;"]
