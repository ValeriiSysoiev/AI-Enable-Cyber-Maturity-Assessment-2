# Azure Storage Configuration

To enable evidence uploads, create a `.env` file in the `app/` directory with the following variables:

```env
# Azure Storage Configuration (optional - for evidence uploads)
# If not configured, the /uploads/sas endpoint will return 501 Not Implemented

# Storage account name (required if using storage)
AZURE_STORAGE_ACCOUNT=staaademo6jshgh

# Option 1: Use Managed Identity (recommended for production)
USE_MANAGED_IDENTITY=true

# Option 2: Use storage account key
# AZURE_STORAGE_KEY=your-storage-account-key-here

# Option 3: Use connection string (alternative to account key)
# AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net

# Container name for evidence uploads (default: docs)
AZURE_STORAGE_CONTAINER=docs

# SAS token TTL in minutes (default: 15)
UPLOAD_SAS_TTL_MINUTES=15
```

## How it works

1. The `/uploads/sas` endpoint checks for Azure Storage configuration
2. If not configured, it returns HTTP 501 (Not Implemented)
3. If configured, it generates a SAS URL with limited permissions and TTL:
   - With Managed Identity: Uses user delegation key (requires Storage Blob Data Contributor role)
   - With account key: Uses traditional account key-based SAS
4. The frontend can then upload directly to Azure Storage using the SAS URL

## Testing

Without configuration:
```bash
curl -s -X POST http://127.0.0.1:8000/uploads/sas \
  -H "Content-Type: application/json" \
  -d '{"blob_name":"evidence/test.txt","permissions":"cw"}'
# Returns 501 with "Evidence uploads not configured"
```

With configuration:
```bash
# Returns SAS URL for direct upload to Azure Storage
```
