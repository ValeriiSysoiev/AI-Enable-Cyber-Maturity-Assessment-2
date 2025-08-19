"""
Minimal FastAPI app for health checks and basic functionality.
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.version_minimal import router as version_router

# Configure basic logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AI Maturity Tool API", version="0.1.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://web-cybermat-prd.azurewebsites.net",
        "https://web-cybermat-stg.azurewebsites.net",
        "*"  # Allow all origins for health checks
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include minimal routes
app.include_router(version_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AI Maturity Tool API is running", "status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)