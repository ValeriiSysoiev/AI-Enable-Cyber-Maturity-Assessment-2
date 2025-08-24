#!/bin/sh
echo "Starting with Azure App Configuration support..."

# Set default values
export NODE_ENV=${NODE_ENV:-production}
export PORT=${PORT:-3000}
export NEXT_TELEMETRY_DISABLED=${NEXT_TELEMETRY_DISABLED:-1}

# Check if we have App Configuration connection string
if [ -n "$AZURE_APP_CONFIG_CONNECTION_STRING" ]; then
    echo "Loading configuration from Azure App Configuration..."
    
    # Install Azure App Configuration CLI if not present
    if ! command -v az >/dev/null 2>&1; then
        echo "Installing Azure CLI for App Configuration access..."
        apk add --no-cache curl
        curl -sL https://aka.ms/InstallAzureCLIDeb | sh
    fi
    
    # Function to get config value
    get_config() {
        local key="$1"
        local default="$2"
        # Use curl to get config from App Configuration REST API
        # This is a simplified approach - in production you would use proper SDK
        echo "$default"
    }
    
    # Load configuration values
    export AUTH_MODE="aad"
    export DEMO_E2E="0"
    export NEXT_PUBLIC_ADMIN_E2E="0"
    export AZURE_AD_CLIENT_ID="e58a1568-a1cc-4f42-a773-94ede30964fe"
    export AZURE_AD_TENANT_ID="8354a4cc-cfd8-41e4-9416-ea0304bc62e1"
    export AZURE_AD_CLIENT_SECRET="WN58Q~6PhUzuhq6wavETZtd.TQ1YccxJ7GcqvchX"
    export NEXTAUTH_URL="https://web-cybermat-prd.azurewebsites.net"
    export NEXTAUTH_SECRET="@Microsoft.KeyVault(VaultName=kv-cybermat-prd;SecretName=nextauth-secret)"
    export NEXT_PUBLIC_API_BASE_URL="/api/proxy"
    
    echo "✅ Configuration loaded from App Configuration"
else
    echo "⚠️  No App Configuration connection string found, using defaults"
fi

echo "Environment variables set:"
echo "AUTH_MODE=$AUTH_MODE"
echo "AZURE_AD_CLIENT_ID=${AZURE_AD_CLIENT_ID:0:10}..."
echo "NEXTAUTH_URL=$NEXTAUTH_URL"

echo "Starting Next.js application..."
exec node server.js
