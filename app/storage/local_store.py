# Local file storage implementation
# This is a stub to prevent import errors during container startup

import os

class LocalStore:
    """Local file storage abstraction"""
    
    def __init__(self, base_path="./data"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def upload(self, data, path):
        """Save data to local file"""
        full_path = os.path.join(self.base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
    
    def download(self, path):
        """Read data from local file"""
        full_path = os.path.join(self.base_path, path)
        with open(full_path, "rb") as f:
            return f.read()