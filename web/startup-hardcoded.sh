#!/bin/sh
echo "Starting with hardcoded environment variables..."

# Set all required environment variables directly
export NODE_ENV="production"
export PORT="3000"
export NEXT_TELEMETRY_DISABLED="1"

# Authentication configuration - hardcoded to fix Azure App Service issue
export AUTH_MODE="aad"
export DEMO_E2E="0"
export NEXT_PUBLIC_ADMIN_E2E="0"
export AZURE_AD_CLIENT_ID="e58a1568-a1cc-4f42-a773-94ede30964fe"
export AZURE_AD_TENANT_ID="8354a4cc-cfd8-41e4-9416-ea0304bc62e1"
export AZURE_AD_CLIENT_SECRET="WN58Q~6PhUzuhq6wavETZtd.TQ1YccxJ7GcqvchX"
export NEXTAUTH_URL="https://web-cybermat-prd.azurewebsites.net"
export NEXTAUTH_SECRET="@Microsoft.KeyVault(VaultName=kv-cybermat-prd;SecretName=nextauth-secret)"
export NEXT_PUBLIC_API_BASE_URL="/api/proxy"
export AUTH_TRUST_HOST="true"

echo "✅ All environment variables set (hardcoded)"
echo "AUTH_MODE=$AUTH_MODE"
echo "AZURE_AD_CLIENT_ID=${AZURE_AD_CLIENT_ID:0:10}..."
echo "NEXTAUTH_URL=$NEXTAUTH_URL"

echo "Starting Next.js application..."
exec node server.js
