import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, generate_container_sas, ContainerSasPermissions
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Configuration from environment
USE_MANAGED_IDENTITY = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
AZURE_STORAGE_KEY = os.getenv("AZURE_STORAGE_KEY")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "docs")
UPLOAD_SAS_TTL_MINUTES = int(os.getenv("UPLOAD_SAS_TTL_MINUTES", "15"))

class SasRequest(BaseModel):
    blob_name: str
    permissions: str = "cw"  # create, write

@router.post("/sas")
def generate_sas_token(request: SasRequest):
    """Generate a SAS token for blob upload. Returns 501 if Azure Storage is not configured."""
    
    # Check if storage is configured
    if not AZURE_STORAGE_ACCOUNT:
        raise HTTPException(
            status_code=501, 
            detail="Evidence uploads not configured. Set AZURE_STORAGE_ACCOUNT"
        )
    
    # Check authentication method
    if USE_MANAGED_IDENTITY:
        # Using Managed Identity (no keys needed)
        pass
    elif not AZURE_STORAGE_KEY and not AZURE_STORAGE_CONNECTION_STRING:
        raise HTTPException(
            status_code=501, 
            detail="Evidence uploads not configured. Set USE_MANAGED_IDENTITY=true or provide AZURE_STORAGE_KEY/CONNECTION_STRING"
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
            account_url = f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"
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
                account_name=AZURE_STORAGE_ACCOUNT,
                container_name=AZURE_STORAGE_CONTAINER,
                blob_name=request.blob_name,
                user_delegation_key=user_delegation_key,
                permission=sas_permissions,
                expiry=expiry_time,
                start=delegation_key_start,
                protocol="https"
            )
        else:
            # Use account key (existing logic)
            if AZURE_STORAGE_KEY:
                account_key = AZURE_STORAGE_KEY
            elif AZURE_STORAGE_CONNECTION_STRING:
                # Extract key from connection string
                import re
                match = re.search(r'AccountKey=([^;]+)', AZURE_STORAGE_CONNECTION_STRING)
                if match:
                    account_key = match.group(1)
                else:
                    raise ValueError("Could not extract AccountKey from connection string")
            else:
                raise ValueError("No valid credentials found")
            
            # Generate SAS token with account key
            sas_token = generate_blob_sas(
                account_name=AZURE_STORAGE_ACCOUNT,
                container_name=AZURE_STORAGE_CONTAINER,
                blob_name=request.blob_name,
                account_key=account_key,
                permission=sas_permissions,
                expiry=expiry_time,
                protocol="https"
            )
        
        # Construct full SAS URL
        sas_url = f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER}/{request.blob_name}?{sas_token}"
        
        return {
            "sasUrl": sas_url,
            "expiresIn": UPLOAD_SAS_TTL_MINUTES * 60,  # seconds
            "container": AZURE_STORAGE_CONTAINER,
            "blobName": request.blob_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SAS token: {str(e)}")
