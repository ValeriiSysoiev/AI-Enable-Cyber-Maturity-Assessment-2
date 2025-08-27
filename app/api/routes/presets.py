import sys
sys.path.append("/app")
from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
import json

from api.security import current_context, require_admin
from services import presets as svc
from api.schemas import AssessmentPreset

router = APIRouter(prefix="/api/presets", tags=["presets"])

@router.get("/")
async def list_presets():
    return await svc.list_presets()

@router.get("/{preset_id}")
async def get_preset(preset_id: str):
    return await svc.get_preset(preset_id)

@router.post("/upload")
async def upload_preset(request: Request, file: Optional[UploadFile] = File(default=None)):
    ctx = await current_context(request)
    require_admin(None, ctx)

    data: Dict[str, Any]
    if file:
        raw = await file.read()
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise HTTPException(400, f"Invalid JSON: {e}")
    else:
        try:
            data = await request.json()
        except Exception as e:
            raise HTTPException(400, f"Invalid JSON body: {e}")

    preset = await svc.save_uploaded_preset(data)
    return JSONResponse({"id": preset.id, "name": preset.name, "version": preset.version})
