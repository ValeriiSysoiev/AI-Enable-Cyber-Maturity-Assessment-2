# Local file storage implementation
# This is a stub to prevent import errors during container startup

import os
import aiofiles
from pathlib import Path

class LocalStore:
    """Local file storage abstraction with async I/O support"""
    
    def __init__(self, base_path="./data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def upload(self, data: bytes, path: str):
        """Save data to local file asynchronously"""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)
    
    async def download(self, path: str) -> bytes:
        """Read data from local file asynchronously"""
        full_path = self.base_path / path
        
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()
    
    # Backward compatibility sync methods (deprecated)
    def upload_sync(self, data, path):
        """Synchronous upload method for backward compatibility"""
        full_path = os.path.join(self.base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
    
    def download_sync(self, path):
        """Synchronous download method for backward compatibility"""
        full_path = os.path.join(self.base_path, path)
        with open(full_path, "rb") as f:
            return f.read()