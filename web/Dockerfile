# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies for building
COPY package.json package-lock.json* ./
RUN npm ci

# Build args that surface through environment for Next.js at build time
ARG NEXT_PUBLIC_API_BASE_URL=""
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# Build args for version information
ARG GITHUB_SHA=""
ARG BUILD_SHA=""
ENV GITHUB_SHA=$GITHUB_SHA
ENV BUILD_SHA=$BUILD_SHA

# Build args for authentication - CRITICAL: These must be in builder stage
# so Next.js can bake them into the standalone build
ARG AUTH_MODE=""
ARG AZURE_AD_CLIENT_ID=""
ARG AZURE_AD_TENANT_ID=""
ARG DEMO_E2E=""
ARG NEXTAUTH_URL=""
ARG PROXY_TARGET_API_BASE_URL=""

# Non-sensitive environment variables
ENV AUTH_MODE=$AUTH_MODE
ENV AZURE_AD_CLIENT_ID=$AZURE_AD_CLIENT_ID
ENV AZURE_AD_TENANT_ID=$AZURE_AD_TENANT_ID
ENV DEMO_E2E=$DEMO_E2E
ENV NEXTAUTH_URL=$NEXTAUTH_URL
ENV PROXY_TARGET_API_BASE_URL=$PROXY_TARGET_API_BASE_URL

# Handle sensitive variables via Docker secrets or runtime injection
# AZURE_AD_CLIENT_SECRET and NEXTAUTH_SECRET will be injected at runtime by Azure Container Apps
# This avoids embedding secrets in the Docker image layers

# Copy source code and build
COPY . .
# Ensure public directory exists for Next.js
RUN mkdir -p public
RUN npm run build

# Runtime stage  
FROM node:20-alpine AS runner
WORKDIR /app

# Set production environment
ENV NODE_ENV=production
# Port configuration - Azure App Service sets PORT to 8080
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1

# Re-expose public env vars for runtime (also embedded at build time)
ARG NEXT_PUBLIC_API_BASE_URL=""
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

# Re-expose version information for runtime
ARG GITHUB_SHA=""
ARG BUILD_SHA=""
ENV GITHUB_SHA=$GITHUB_SHA
ENV BUILD_SHA=$BUILD_SHA

# Note: Azure App Service will inject environment variables at runtime
# Next.js standalone mode will read them via next.config.js

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Install curl for health checks
RUN apk add --no-cache curl

# Copy the standalone build from builder stage
# Next.js standalone build includes server.js and all required dependencies
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy public files if they exist
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Switch to non-root user
USER nextjs

# Expose port 3000 (Azure App Service will map this to its PORT)
EXPOSE 3000

# Health check - use the Azure App Service PORT if available, otherwise default to 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-3000}/ || exit 1

# Start the application using the generated server.js from standalone build
# This uses Node.js directly without requiring Next.js CLI in production
# The standalone build respects the PORT environment variable
CMD ["node", "server.js"]