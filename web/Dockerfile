# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies for building
COPY package.json package-lock.json* ./
RUN npm ci

# Build args that surface through environment for Next.js at build time
ARG NEXT_PUBLIC_API_BASE_URL=""
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

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

# Copy startup script for Azure App Service environment variable workaround
COPY --from=builder --chown=nextjs:nodejs /app/startup.sh ./startup.sh

# Switch to non-root user
USER nextjs

# Expose port 3000 (Azure App Service will map this to its PORT)
EXPOSE 3000

# Health check - use the Azure App Service PORT if available, otherwise default to 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-3000}/ || exit 1

# Start the application using startup script that handles Azure App Service environment variables
CMD ["sh", "./startup.sh"]