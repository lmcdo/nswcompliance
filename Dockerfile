# PRP-A3: Production Docker Configuration
# Multi-stage build for optimized cloud deployment

# Stage 1: Base dependencies
FROM node:20-alpine AS base

# Install security updates and required packages
RUN apk update && apk upgrade && \
    apk add --no-cache \
    dumb-init \
    postgresql-client \
    curl \
    && rm -rf /var/cache/apk/*

# Create app user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY frontend-nextjs/package*.json ./frontend-nextjs/

# Stage 2: Dependencies
FROM base AS deps

# Install all dependencies
RUN npm ci --only=production && npm cache clean --force

# Install frontend dependencies
WORKDIR /app/frontend-nextjs
RUN npm ci --only=production && npm cache clean --force

# Stage 3: Build
FROM base AS builder

# Copy all dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/frontend-nextjs/node_modules ./frontend-nextjs/node_modules

# Copy source code
COPY . .

# Build Next.js application
WORKDIR /app/frontend-nextjs
RUN npm run build

# Stage 4: Production runtime
FROM base AS runner

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy built application
COPY --from=builder --chown=nextjs:nodejs /app/frontend-nextjs/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/frontend-nextjs/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/frontend-nextjs/public ./public

# Copy configuration files
COPY --from=builder --chown=nextjs:nodejs /app/config ./config

# Copy Python scripts (for backwards compatibility)
COPY --from=builder --chown=nextjs:nodejs /app/*.py ./
COPY --from=builder --chown=nextjs:nodejs /app/db_safety_wrapper.py ./
COPY --from=builder --chown=nextjs:nodejs /app/backup_manager.py ./

# Create necessary directories
RUN mkdir -p /app/logs /app/backups && \
    chown -R nextjs:nodejs /app/logs /app/backups

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health?type=liveness || exit 1

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Set environment variables for containerized deployment
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start application with dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]