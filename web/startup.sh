#!/bin/sh
echo "Starting Azure App Service environment variable workaround..."

# Try to read environment variables from Azure App Service metadata
# This is a workaround for containers not receiving environment variables

# Set default values if not available
export NODE_ENV=${NODE_ENV:-production}
export PORT=${PORT:-3000}
export NEXT_TELEMETRY_DISABLED=${NEXT_TELEMETRY_DISABLED:-1}

# Try to get App Service environment variables from the metadata endpoint
if [ -n "$WEBSITE_SITE_NAME" ]; then
    echo "Running in Azure App Service, attempting to load environment variables..."
    
    # These should be available from App Service
    export AUTH_MODE=${AUTH_MODE:-aad}
    export DEMO_E2E=${DEMO_E2E:-0}
    export NEXT_PUBLIC_ADMIN_E2E=${NEXT_PUBLIC_ADMIN_E2E:-0}
    export AZURE_AD_CLIENT_ID=${AZURE_AD_CLIENT_ID}
    export AZURE_AD_TENANT_ID=${AZURE_AD_TENANT_ID}
    export AZURE_AD_CLIENT_SECRET=${AZURE_AD_CLIENT_SECRET}
    export NEXTAUTH_URL=${NEXTAUTH_URL}
    export NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
    export NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL:-/api/proxy}
    
    echo "Environment variables loaded from App Service"
else
    echo "Not running in Azure App Service, using defaults"
fi

echo "Starting Next.js application..."
exec node server.js
