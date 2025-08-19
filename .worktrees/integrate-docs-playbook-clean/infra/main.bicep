// Bicep skeleton – expand with real parameters and identities for production
param location string = resourceGroup().location
param baseName string = 'cyberai${uniqueString(resourceGroup().id)}'

// Log Analytics
resource logws 'Microsoft.OperationalInsights/workspaces@2021-12-01-preview' = {
  name: '${baseName}-log'
  location: location
  properties: { retentionInDays: 30 }
}

// Application Insights
resource appins 'Microsoft.Insights/components@2020-02-02' = {
  name: '${baseName}-appi'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logws.id
  }
}

// Key Vault
resource kv 'Microsoft.KeyVault/vaults@2022-07-01' = {
  name: '${baseName}-kv'
  location: location
  properties: {
    sku: { name: 'standard', family: 'A' }
    tenantId: subscription().tenantId
    accessPolicies: []
    enablePurgeProtection: true
    enableRbacAuthorization: true
  }
}

// Cosmos DB (stub account)
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: '${baseName}-cosmos'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [ { locationName: location } ]
    capabilities: [ { name: 'EnableServerless' } ]
  }
}

// Service Bus (future async orchestration)
resource sb 'Microsoft.ServiceBus/namespaces@2021-11-01' = {
  name: '${baseName}-sb'
  location: location
  sku: { name: 'Basic', tier: 'Basic' }
}

// Container Apps Environment
resource cae 'Microsoft.App/managedEnvironments@2024-02-02-preview' = {
  name: '${baseName}-cae'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logws.properties.customerId
        sharedKey: logws.listKeys().primarySharedKey
      }
    }
  }
}

// Note: Define Container Apps per service referencing images pushed to ACR (not included in this stub).
