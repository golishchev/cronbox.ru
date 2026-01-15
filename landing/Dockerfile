# Landing Dockerfile - Next.js Multi-stage build
# Optimized for production with standalone output

# Dependencies stage
FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Builder stage
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Environment variables for build
ARG NEXT_PUBLIC_API_URL=https://api.cronbox.ru/v1

# Build Next.js app with standalone output
RUN NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} npm run build

# Production stage
FROM node:20-alpine AS runner
WORKDIR /app

# Security labels
LABEL maintainer="CronBox Team"
LABEL version="2.0"
LABEL description="CronBox Landing (Next.js)"

# Environment
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Copy built files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Security: Non-root user (node user already exists in alpine with uid 1000)
USER node

EXPOSE 3000

# Health check using Node.js fetch (wget unreliable in alpine)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
