from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Dict
import json

from ..security import current_context, require_admin
from ...services import presets as svc
from ..schemas import AssessmentPreset

router = APIRouter(prefix="/presets", tags=["presets"])

@router.get("/")
def list_presets():
    return svc.list_presets()

@router.get("/{preset_id}")
def get_preset(preset_id: str):
    return svc.get_preset(preset_id)

@router.post("/upload")
async def upload_preset(request: Request, file: UploadFile | None = File(default=None)):
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

    preset = svc.save_uploaded_preset(data)
    return JSONResponse({"id": preset.id, "name": preset.name, "version": preset.version})
