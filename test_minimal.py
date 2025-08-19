from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(title="Minimal Test API")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Minimal FastAPI test successful"
    }

@app.get("/")
async def root():
    return {"message": "Minimal test API is running"}