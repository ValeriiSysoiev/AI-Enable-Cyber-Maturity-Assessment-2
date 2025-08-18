import os
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, generate_container_sas, ContainerSasPermissions
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from security.secret_provider import get_secret

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Configuration from environment (will be enhanced with secret provider)
USE_MANAGED_IDENTITY = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
UPLOAD_SAS_TTL_MINUTES = int(os.getenv("UPLOAD_SAS_TTL_MINUTES", "15"))

# Configuration will be loaded from secret provider
AZURE_STORAGE_ACCOUNT = None
AZURE_STORAGE_KEY = None
AZURE_STORAGE_CONNECTION_STRING = None
AZURE_STORAGE_CONTAINER = None

async def _get_storage_config(correlation_id: str = None):
    """Get storage configuration from secret provider"""
    global AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY, AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER
    
    # Get secrets from secret provider
    account = await get_secret("azure-storage-account", correlation_id)
    key = await get_secret("azure-storage-key", correlation_id)
    connection_string = await get_secret("azure-storage-connection-string", correlation_id)
    container = await get_secret("azure-storage-container", correlation_id)
    
    # Fallback to environment variables for local development
    AZURE_STORAGE_ACCOUNT = account or os.getenv("AZURE_STORAGE_ACCOUNT")
    AZURE_STORAGE_KEY = key or os.getenv("AZURE_STORAGE_KEY")
    AZURE_STORAGE_CONNECTION_STRING = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER = container or os.getenv("AZURE_STORAGE_CONTAINER", "docs")
    
    return {
        "account": AZURE_STORAGE_ACCOUNT,
        "key": AZURE_STORAGE_KEY,
        "connection_string": AZURE_STORAGE_CONNECTION_STRING,
        "container": AZURE_STORAGE_CONTAINER
    }

class SasRequest(BaseModel):
    blob_name: str
    permissions: str = "cw"  # create, write

@router.post("/sas")
async def generate_sas_token(request: SasRequest):
    """Generate a SAS token for blob upload. Returns 501 if Azure Storage is not configured."""
    
    # Get storage configuration from secret provider
    storage_config = await _get_storage_config()
    
    # Check if storage is configured
    if not storage_config["account"]:
        raise HTTPException(
            status_code=501, 
            detail="Evidence uploads not configured. Set azure-storage-account secret or AZURE_STORAGE_ACCOUNT"
        )
    
    # Check authentication method
    if USE_MANAGED_IDENTITY:
        # Using Managed Identity (no keys needed)
        pass
    elif not storage_config["key"] and not storage_config["connection_string"]:
        raise HTTPException(
            status_code=501, 
            detail="Evidence uploads not configured. Set USE_MANAGED_IDENTITY=true or provide azure-storage-key/connection-string secrets"
        )
    
    try:
        # Calculate expiry time
        expiry_time = datetime.utcnow() + timedelta(minutes=UPLOAD_SAS_TTL_MINUTES)
        
        # Parse permissions
        sas_permissions = BlobSasPermissions()
        if 'r' in request.permissions:
            sas_permissions.read = True
        if 'w' in request.permissions:
            sas_permissions.write = True
        if 'c' in request.permissions:
            sas_permissions.create = True
        if 'd' in request.permissions:
            sas_permissions.delete = True
        
        if USE_MANAGED_IDENTITY:
            # Use Managed Identity with user delegation key
            account_url = f"https://{storage_config['account']}.blob.core.windows.net"
            blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=DefaultAzureCredential()
            )
            
            # Get user delegation key (valid for 1 hour)
            delegation_key_start = datetime.utcnow()
            delegation_key_expiry = delegation_key_start + timedelta(hours=1)
            user_delegation_key = blob_service_client.get_user_delegation_key(
                key_start_time=delegation_key_start,
                key_expiry_time=delegation_key_expiry
            )
            
            # Generate user delegation SAS
            sas_token = generate_blob_sas(
                account_name=storage_config["account"],
                container_name=storage_config["container"],
                blob_name=request.blob_name,
                user_delegation_key=user_delegation_key,
                permission=sas_permissions,
                expiry=expiry_time,
                start=delegation_key_start,
                protocol="https"
            )
        else:
            # Use account key (existing logic)
            if storage_config["key"]:
                account_key = storage_config["key"]
            elif storage_config["connection_string"]:
                # Extract key from connection string
                import re
                match = re.search(r'AccountKey=([^;]+)', storage_config["connection_string"])
                if match:
                    account_key = match.group(1)
                else:
                    raise ValueError("Could not extract AccountKey from connection string")
            else:
                raise ValueError("No valid credentials found")
            
            # Generate SAS token with account key
            sas_token = generate_blob_sas(
                account_name=storage_config["account"],
                container_name=storage_config["container"],
                blob_name=request.blob_name,
                account_key=account_key,
                permission=sas_permissions,
                expiry=expiry_time,
                protocol="https"
            )
        
        # Construct full SAS URL
        sas_url = f"https://{storage_config['account']}.blob.core.windows.net/{storage_config['container']}/{request.blob_name}?{sas_token}"
        
        return {
            "sasUrl": sas_url,
            "expiresIn": UPLOAD_SAS_TTL_MINUTES * 60,  # seconds
            "container": storage_config["container"],
            "blobName": request.blob_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SAS token: {str(e)}")
