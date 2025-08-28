#!/bin/bash

# Deploy to Azure Container Apps
echo "Deploying to Azure Container Apps..."

# Set variables
RESOURCE_GROUP="rg-cybermat-prd"
CONTAINER_APP_NAME="api-cybermat-prd-aca"
REGISTRY="apimaturityreg"
IMAGE_TAG="latest"

# Build and push Docker image
echo "Building Docker image..."
cd app
docker build -t $REGISTRY.azurecr.io/api:$IMAGE_TAG .

# Login to ACR
echo "Logging in to Azure Container Registry..."
az acr login --name $REGISTRY

# Push image
echo "Pushing Docker image..."
docker push $REGISTRY.azurecr.io/api:$IMAGE_TAG

# Update Container App
echo "Updating Container App with new image..."
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $REGISTRY.azurecr.io/api:$IMAGE_TAG

# Get the URL
FQDN=$(az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Container App updated successfully!"
echo "API URL: https://$FQDN"
echo "Health endpoint: https://$FQDN/health"

# Test the health endpoint
echo ""
echo "Testing health endpoint..."
curl -s "https://$FQDN/health" | jq .