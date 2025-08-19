"""
Minimal FastAPI test app for diagnosing startup issues.
This app has minimal dependencies and no complex module imports.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import os
import sys
from datetime import datetime

# Create FastAPI app with minimal configuration
app = FastAPI(
    title="Test API",
    description="Minimal FastAPI app for debugging startup issues",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Test API is running", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/debug")
async def debug():
    """Debug information endpoint"""
    return {
        "status": "ok",
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "environment_vars": {
            "PORT": os.getenv("PORT", "not_set"),
            "PYTHONPATH": os.getenv("PYTHONPATH", "not_set"),
            "PATH": os.getenv("PATH", "truncated")[:200] + "..." if len(os.getenv("PATH", "")) > 200 else os.getenv("PATH", "not_set")
        },
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)